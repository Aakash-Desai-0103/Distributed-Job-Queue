#!/usr/bin/env python3
# tests/test_malformed.py

import socket
import ssl
import sys
import json


class MalformedRequestTester:
    def __init__(self, server_host, server_port=9999):
        self.server_host = server_host
        self.server_port = server_port
        self.socket = None
        self.test_results = []
        self.receive_buffer = ""

    def connect(self):
        """Connect to server with SSL"""
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket = context.wrap_socket(
            sock,
            server_hostname=self.server_host
        )
        self.socket.connect((self.server_host, self.server_port))
        print(f"[+] Connected to {self.server_host}:{self.server_port}")

    def send_raw(self, message, timeout=5):
        """Send raw data and receive one JSON response"""
        try:
            self.socket.settimeout(timeout)
            self.socket.sendall((message + "\n").encode("utf-8"))

            while "\n" not in self.receive_buffer:
                try:
                    chunk = self.socket.recv(4096).decode("utf-8")

                    if not chunk:
                        return {
                            "type": "CONNECTION_CLOSED"
                        }

                    self.receive_buffer += chunk

                except socket.timeout:
                    return {
                        "type": "TIMEOUT"
                    }

            line, self.receive_buffer = self.receive_buffer.split("\n", 1)

            try:
                return json.loads(line)
            except json.JSONDecodeError:
                return {
                    "type": "INVALID_RESPONSE",
                    "raw": line
                }

        except Exception as e:
            return {
                "type": "EXCEPTION",
                "message": str(e)
            }

    def send_json(self, message, timeout=5):
        return self.send_raw(
            json.dumps(message),
            timeout
        )

    def run_raw_test(self, test_name, message, expected_type="ERROR"):
        print(f"\n[TEST] {test_name}")
        print(f"  Sending raw: {repr(message)}")

        response = self.send_raw(message)
        print(f"  Response: {response}")

        if response.get("type") == expected_type:
            print("  ✅ PASS - Got expected response")
            self.test_results.append((test_name, "PASS"))
            return True

        print(f"  ❌ FAIL - Expected response type '{expected_type}'")
        self.test_results.append((test_name, "FAIL"))
        return False

    def run_json_test(self, test_name, message, expected_type="ERROR"):
        print(f"\n[TEST] {test_name}")
        print(f"  Sending JSON: {message}")

        response = self.send_json(message)
        print(f"  Response: {response}")

        if response.get("type") == expected_type:
            print("  ✅ PASS - Got expected response")
            self.test_results.append((test_name, "PASS"))
            return True

        print(f"  ❌ FAIL - Expected response type '{expected_type}'")
        self.test_results.append((test_name, "FAIL"))
        return False

    def run_all_tests(self):
        print("\n" + "="*60)
        print("ERROR HANDLING & MALFORMED JSON TESTS")
        print("="*60)

        self.run_raw_test(
            "Plain text instead of JSON",
            "INVALID_COMMAND"
        )

        self.run_raw_test(
            "Broken JSON",
            '{"type": "SUBMIT_JOB", "job_type": "factorial"'
        )

        self.run_raw_test(
            "Invalid JSON syntax",
            '{"type": SUBMIT_JOB}'
        )

        self.run_json_test(
            "JSON array instead of object",
            ["SUBMIT_JOB", "factorial"]
        )

        self.run_json_test(
            "Missing message type",
            {
                "job_type": "factorial",
                "parameters": {
                    "n": 5
                }
            }
        )

        self.run_json_test(
            "Unknown message type",
            {
                "type": "INVALID_COMMAND"
            }
        )

        self.run_json_test(
            "SUBMIT_JOB missing job type",
            {
                "type": "SUBMIT_JOB",
                "parameters": {
                    "n": 5
                }
            }
        )

        self.run_json_test(
            "SUBMIT_JOB invalid job type",
            {
                "type": "SUBMIT_JOB",
                "job_type": 123,
                "parameters": {
                    "n": 5
                }
            }
        )

        self.run_json_test(
            "SUBMIT_JOB parameters not object",
            {
                "type": "SUBMIT_JOB",
                "job_type": "factorial",
                "parameters": "n=5"
            }
        )

        self.run_json_test(
            "REQUEST_JOB missing worker ID",
            {
                "type": "REQUEST_JOB"
            }
        )

        self.run_json_test(
            "COMPLETE missing job ID",
            {
                "type": "COMPLETE",
                "worker_id": "worker_test",
                "result": 120
            }
        )

        self.run_json_test(
            "COMPLETE missing result",
            {
                "type": "COMPLETE",
                "job_id": "job_1",
                "worker_id": "worker_test"
            }
        )

        self.run_json_test(
            "GETRESULT missing job ID",
            {
                "type": "GETRESULT"
            }
        )

        self.run_json_test(
            "HEARTBEAT missing worker ID",
            {
                "type": "HEARTBEAT"
            }
        )

        self.run_json_test(
            "Extremely long job type",
            {
                "type": "SUBMIT_JOB",
                "job_type": "A" * 10000,
                "parameters": {}
            }
        )

        print("\n[TEST] Valid command after errors")

        response = self.send_json({
            "type": "SUBMIT_JOB",
            "job_type": "factorial",
            "parameters": {
                "n": 5
            }
        })

        print(f"  Response: {response}")

        if response.get("type") == "OK" and response.get("job_id"):
            print("  ✅ PASS - Server still functioning correctly")
            self.test_results.append(("Server recovery", "PASS"))
        else:
            print("  ❌ FAIL - Server may not have recovered correctly")
            self.test_results.append(("Server recovery", "FAIL"))

        self.run_json_test(
            "GETRESULT for non-existent job",
            {
                "type": "GETRESULT",
                "job_id": "job_99999"
            },
            "RESULT"
        )

        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)

        passed = sum(
            1 for _, result in self.test_results
            if result == "PASS"
        )

        failed = sum(
            1 for _, result in self.test_results
            if result == "FAIL"
        )

        for test_name, result in self.test_results:
            symbol = "✅" if result == "PASS" else "❌"
            print(f"{symbol} {test_name}: {result}")

        print(
            f"\nTotal: {passed} passed, "
            f"{failed} failed out of {len(self.test_results)}"
        )

        if failed == 0:
            print("\n✅ ALL TESTS PASSED - Server handles errors correctly!")
        else:
            print(
                f"\n⚠️ {failed} test(s) failed - "
                "Review server error handling"
            )

        print("="*60)
        return failed == 0

    def close(self):
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass

            print("\n[!] Connection closed")


if __name__ == "__main__":
    SERVER_IP = '127.0.0.1'

    print("\n" + "="*60)
    print("MALFORMED JSON REQUEST TESTING")
    print("Testing server error handling")
    print("="*60)

    tester = MalformedRequestTester(SERVER_IP)

    try:
        tester.connect()
        success = tester.run_all_tests()
        tester.close()

        if success:
            print("\n✅ Error handling verification complete!")
            sys.exit(0)

        print("\n⚠️ Some edge cases need attention")
        sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n[!] Test interrupted by user")
        sys.exit(1)

    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
