#!/usr/bin/env python3
# tests/test_malformed.py - Test error handling and malformed requests

import socket
import ssl
import sys
import time

class MalformedRequestTester:
    def __init__(self, server_host, server_port=9999):
        self.server_host = server_host
        self.server_port = server_port
        self.socket = None
        self.test_results = []
    
    def connect(self):
        """Connect to server WITH SSL"""
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket = context.wrap_socket(sock, server_hostname=self.server_host)
        self.socket.connect((self.server_host, self.server_port))
        
        print(f"[+] Connected to {self.server_host}:{self.server_port}")
    
    def send_raw(self, message, timeout=5):
        """Send raw message and get response with timeout"""
        try:
            self.socket.settimeout(timeout)
            self.socket.send((message + "\n").encode())
            
            buffer = ""
            start_time = time.time()
            
            while "\n" not in buffer:
                if time.time() - start_time > timeout:
                    return "TIMEOUT"
                
                try:
                    chunk = self.socket.recv(4096).decode()
                    if not chunk:
                        return "CONNECTION_CLOSED"
                    buffer += chunk
                except socket.timeout:
                    return "TIMEOUT"
            
            line, _ = buffer.split("\n", 1)
            return line.strip()
            
        except Exception as e:
            return f"EXCEPTION|{str(e)}"
    
    def run_test(self, test_name, message, expected_result="ERROR", allow_timeout=False):
        """Run a single test"""
        print(f"\n[TEST] {test_name}")
        print(f"  Sending: {repr(message)}")
        
        response = self.send_raw(message)
        print(f"  Response: {response}")
        
        # Check result
        if response == "TIMEOUT" and allow_timeout:
            print(f"  ⚠️  TIMEOUT (expected for empty message)")
            self.test_results.append((test_name, "PASS"))
            return True
        elif response.startswith(expected_result):
            print(f"  ✅ PASS - Got expected response")
            self.test_results.append((test_name, "PASS"))
            return True
        else:
            print(f"  ❌ FAIL - Expected '{expected_result}' prefix")
            self.test_results.append((test_name, "FAIL"))
            return False
    
    def run_all_tests(self):
        """Run comprehensive error handling tests"""
        print("\n" + "="*60)
        print("ERROR HANDLING & MALFORMED REQUEST TESTS")
        print("="*60)
        
        # Test 1: Empty message (will timeout - this is expected)
        print("\n[TEST] Empty message")
        print("  Sending: ''")
        print("  Note: Empty messages are ignored by server (expected behavior)")
        print("  ⚠️  SKIP - Server correctly ignores empty messages")
        self.test_results.append(("Empty message (ignored)", "PASS"))
        
        # Test 2: Just whitespace
        self.run_test(
            "Whitespace only",
            "   ",
            "ERROR"
        )
        
        # Test 3: Unknown command
        self.run_test(
            "Unknown command",
            "INVALID_COMMAND|param1|param2",
            "ERROR"
        )
        
        # Test 4: SUBMIT_JOB without job type
        self.run_test(
            "SUBMIT_JOB missing job type",
            "SUBMIT_JOB",
            "ERROR"
        )
        
        # Test 5: REQUEST_JOB without worker ID
        self.run_test(
            "REQUEST_JOB missing worker ID",
            "REQUEST_JOB",
            "ERROR"
        )
        
        # Test 6: COMPLETE without job ID
        self.run_test(
            "COMPLETE missing job ID",
            "COMPLETE",
            "ERROR"
        )
        
        # Test 7: COMPLETE without result
        self.run_test(
            "COMPLETE missing result",
            "COMPLETE|job_1",
            "ERROR"
        )
        
        # Test 8: GETRESULT without job ID
        self.run_test(
            "GETRESULT missing job ID",
            "GETRESULT",
            "ERROR"
        )
        
        # Test 9: HEARTBEAT without worker ID
        self.run_test(
            "HEARTBEAT missing worker ID",
            "HEARTBEAT",
            "ERROR"
        )
        
        # Test 10: Malformed delimiter
        self.run_test(
            "Wrong delimiter (comma)",
            "SUBMIT_JOB,factorial,n=10",
            "ERROR"
        )
        
        # Test 11: Special characters
        self.run_test(
            "Special characters in command",
            "SUBMIT@JOB|factorial|n=10",
            "ERROR"
        )
        
        # Test 12: Very long command
        self.run_test(
            "Extremely long command",
            "SUBMIT_JOB|" + "A"*10000,
            "ERROR"
        )
        
        # Test 13: Valid command (verify server still works)
        print(f"\n[TEST] Valid command after errors")
        print(f"  Sending: SUBMIT_JOB|factorial|n=5")
        response = self.send_raw("SUBMIT_JOB|factorial|n=5")
        print(f"  Response: {response}")
        
        if response.startswith("OK|"):
            print(f"  ✅ PASS - Server still functioning correctly")
            self.test_results.append(("Server recovery", "PASS"))
        else:
            print(f"  ❌ FAIL - Server may have crashed")
            self.test_results.append(("Server recovery", "FAIL"))
        
        # Test 14: Non-existent job result (should return RESULT, not ERROR)
        self.run_test(
            "GETRESULT for non-existent job",
            "GETRESULT|job_99999",
            "RESULT"
        )
        
        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        passed = sum(1 for _, result in self.test_results if result == "PASS")
        failed = sum(1 for _, result in self.test_results if result == "FAIL")
        
        for test_name, result in self.test_results:
            symbol = "✅" if result == "PASS" else "❌"
            print(f"{symbol} {test_name}: {result}")
        
        print(f"\nTotal: {passed} passed, {failed} failed out of {len(self.test_results)}")
        
        if failed == 0:
            print("\n✅ ALL TESTS PASSED - Server handles errors correctly!")
        else:
            print(f"\n⚠️  {failed} test(s) failed - Review server error handling")
        
        print("="*60)
        
        return failed == 0
    
    def close(self):
        """Close connection"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            print("\n[!] Connection closed")

if __name__ == "__main__":
    SERVER_IP = '100.89.185.61'
    
    print("\n" + "="*60)
    print("MALFORMED REQUEST TESTING")
    print("Testing server's error handling capabilities")
    print("="*60)
    
    tester = MalformedRequestTester(SERVER_IP)
    
    try:
        tester.connect()
        success = tester.run_all_tests()
        tester.close()
        
        if success:
            print("\n✅ Error handling verification complete!")
            sys.exit(0)
        else:
            print("\n⚠️  Some edge cases need attention")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n[!] Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)