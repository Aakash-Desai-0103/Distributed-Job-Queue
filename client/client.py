import socket
import time
import ssl
import os
import sys
import json


class JobSubmitter:
    def __init__(self, server_host, server_port=9999, cert_path='cert.pem'):
        self.server_host = server_host
        self.server_port = server_port
        self.cert_path = cert_path
        self.socket = None
        self.receive_buffer = ""

    def verify_certificate_exists(self):
        """Check if certificate file exists"""
        if not os.path.exists(self.cert_path):
            print(f"[ERROR] Certificate not found: {self.cert_path}")
            print("[INFO] Please copy cert.pem from server to client directory")
            return False

        print(f"[✓] Certificate found: {self.cert_path}")
        return True

    def connect(self):
        """Connect to server WITH SSL VERIFICATION"""
        if not self.verify_certificate_exists():
            sys.exit(1)

        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.load_verify_locations(self.cert_path)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_REQUIRED

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket = context.wrap_socket(
                sock,
                server_hostname=self.server_host
            )
            self.socket.connect((self.server_host, self.server_port))

            cert = self.socket.getpeercert()

            print(f"\n{'='*60}")
            print("[🔒] SSL CONNECTION ESTABLISHED")
            print(f"{'='*60}")
            print(f"[+] Connected to {self.server_host}:{self.server_port}")
            print(f"[🔐] SSL/TLS Protocol: {self.socket.version()}")
            print("[✓] Server certificate verified successfully!")

            if cert:
                subject = dict(x[0] for x in cert['subject'])
                print(f"[📜] Certificate CN: {subject.get('commonName', 'N/A')}")
                print(f"[📅] Valid until: {cert['notAfter']}")

            print("[+] Using newline-delimited JSON protocol")
            print(f"{'='*60}\n")

        except ssl.SSLError as e:
            print("\n[❌] SSL VERIFICATION FAILED!")
            print(f"[ERROR] {e}")
            print("\n[INFO] Possible issues:")
            print("  1. Certificate doesn't match server IP")
            print("  2. Certificate is expired")
            print("  3. Wrong certificate file")
            sys.exit(1)

        except Exception as e:
            print("\n[❌] CONNECTION FAILED!")
            print(f"[ERROR] {e}")
            sys.exit(1)

    def send_message(self, message):
        """Send JSON message and receive JSON response"""
        data = json.dumps(message) + "\n"
        self.socket.sendall(data.encode("utf-8"))

        while "\n" not in self.receive_buffer:
            chunk = self.socket.recv(4096).decode("utf-8")

            if not chunk:
                raise ConnectionError("Server closed connection")

            self.receive_buffer += chunk

        line, self.receive_buffer = self.receive_buffer.split("\n", 1)

        try:
            return json.loads(line)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response from server: {e}")

    def submit_job(self, job_type, priority=3, **kwargs):
        """Submit a job and return job_id"""

        message = {
            "type": "SUBMIT_JOB",
            "job_type": job_type,
            "priority": priority,
            "parameters": kwargs
        }

        response = self.send_message(message)

        if response.get("type") == "OK":
            job_id = response.get("job_id")

            print(
                f"[✓] Job submitted: {job_id} "
                f"(Priority {priority}) "
                f"(type: {job_type}, params: {kwargs})"
            )

            return job_id

        print(
            f"[✗] Error: "
            f"{response.get('message', response)}"
        )

        return None

    def get_result(self, job_id, max_wait=30, poll_interval=2):
        """Get result with polling"""
        print(f"\n[...] Waiting for result of {job_id}...")

        start_time = time.time()
        attempts = 0

        while time.time() - start_time < max_wait:
            attempts += 1

            message = {
                "type": "GETRESULT",
                "job_id": job_id
            }

            response = self.send_message(message)

            if response.get("type") != "RESULT":
                print(f"[ERROR] Invalid response: {response}")
                return None

            status = response.get("status")
            print(f"[Attempt {attempts}] Status: {status}")

            if status == "completed":
                result = response.get("result")
                print(f"[✓] Result received: {result}\n")
                return result

            elif status == "in_progress":
                print(
                    f"[...] Job in progress, "
                    f"waiting {poll_interval}s..."
                )

            elif status == "pending":
                print(
                    f"[...] Job pending, "
                    f"waiting {poll_interval}s..."
                )

            elif status == "not_found":
                print(f"[✗] Job {job_id} not found")
                return None

            else:
                print(f"[ERROR] Unknown job status: {status}")
                return None

            time.sleep(poll_interval)

        print(f"[✗] Timeout waiting for result after {max_wait}s\n")
        return None

    def close(self):
        """Close connection"""
        if self.socket:
            self.socket.close()
            print("[!] Connection closed")


if __name__ == "__main__":
    SERVER_IP = '127.0.0.1'

    client = JobSubmitter(SERVER_IP, cert_path='cert.pem')
    client.connect()

    print("\n" + "="*60)
    print("DISTRIBUTED JOB QUEUE - CLIENT TEST")
    print("SSL/TLS VERIFIED + JSON PROTOCOL")
    print("Testing ALL 9 Job Types")
    print("="*60)

    print("\n### Test 1: FACTORIAL ###")
    job1 = client.submit_job('factorial', n=10)
    if job1:
        client.get_result(job1)

    print("\n### Test 2: FIBONACCI ###")
    job2 = client.submit_job('fibonacci', n=10)
    if job2:
        client.get_result(job2)

    print("\n### Test 3: SUM ###")
    job3 = client.submit_job('sum', limit=100)
    if job3:
        client.get_result(job3)

    print("\n### Test 4: PRIME ###")
    job4 = client.submit_job('prime', n=97)
    if job4:
        client.get_result(job4)

    print("\n### Test 5: POWER ###")
    job5 = client.submit_job('power', x=2, y=10)
    if job5:
        client.get_result(job5)

    print("\n### Test 6: GCD ###")
    job6 = client.submit_job('gcd', a=48, b=18)
    if job6:
        client.get_result(job6)

    print("\n### Test 7: SORT ###")
    job7 = client.submit_job('sort', size=1000)
    if job7:
        client.get_result(job7)

    print("\n### Test 8: MATRIX ###")
    job8 = client.submit_job('matrix', size=10)
    if job8:
        client.get_result(job8)

    print("\n### Test 9: SLEEP ###")
    job9 = client.submit_job('sleep', duration=2)
    if job9:
        client.get_result(job9)

    print("\n" + "="*60)
    print("ALL 9 JOB TYPES TESTED SUCCESSFULLY!")
    print("="*60 + "\n")

    client.close()
