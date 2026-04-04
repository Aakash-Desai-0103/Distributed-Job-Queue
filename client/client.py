import socket
import time
import ssl
import os
import sys

class JobSubmitter:
    def __init__(self, server_host, server_port=9999, cert_path='cert.pem'):
        self.server_host = server_host
        self.server_port = server_port
        self.cert_path = cert_path
        self.socket = None
    
    def verify_certificate_exists(self):
        """Check if certificate file exists"""
        if not os.path.exists(self.cert_path):
            print(f"[ERROR] Certificate not found: {self.cert_path}")
            print(f"[INFO] Please copy cert.pem from server to client directory")
            return False
        
        print(f"[✓] Certificate found: {self.cert_path}")
        return True
    
    def connect(self):
        """Connect to server WITH SSL VERIFICATION"""
        
        # Verify certificate exists
        if not self.verify_certificate_exists():
            sys.exit(1)
        
        # Create SSL context with VERIFICATION
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.load_verify_locations(self.cert_path)
        
        # ENABLE certificate verification
        context.check_hostname = False  # Using IP, not hostname
        context.verify_mode = ssl.CERT_REQUIRED
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket = context.wrap_socket(sock, server_hostname=self.server_host)
            self.socket.connect((self.server_host, self.server_port))
            
            # Get certificate info
            cert = self.socket.getpeercert()
            
            print(f"\n{'='*60}")
            print(f"[🔒] SSL CONNECTION ESTABLISHED")
            print(f"{'='*60}")
            print(f"[+] Connected to {self.server_host}:{self.server_port}")
            print(f"[🔐] SSL/TLS Protocol: {self.socket.version()}")
            print(f"[✓] Server certificate verified successfully!")
            
            if cert:
                subject = dict(x[0] for x in cert['subject'])
                print(f"[📜] Certificate CN: {subject.get('commonName', 'N/A')}")
                print(f"[📅] Valid until: {cert['notAfter']}")
            
            print(f"[+] Using PLAIN TEXT protocol (pipe-delimited)")
            print(f"{'='*60}\n")
            
        except ssl.SSLError as e:
            print(f"\n[❌] SSL VERIFICATION FAILED!")
            print(f"[ERROR] {e}")
            print(f"\n[INFO] Possible issues:")
            print(f"  1. Certificate doesn't match server IP")
            print(f"  2. Certificate is expired")
            print(f"  3. Wrong certificate file")
            sys.exit(1)
        except Exception as e:
            print(f"\n[❌] CONNECTION FAILED!")
            print(f"[ERROR] {e}")
            sys.exit(1)
    
    def send_message(self, message):
        """Send message and get response"""
        self.socket.send((message + "\n").encode())
        
        buffer = ""
        while "\n" not in buffer:
            chunk = self.socket.recv(4096).decode()
            if not chunk:
                raise ConnectionError("Server closed connection")
            buffer += chunk
        
        line, _ = buffer.split("\n", 1)
        return line.strip()
    
    def submit_job(self, job_type, **kwargs):
        """Submit a job and return job_id"""
        message = f"SUBMIT_JOB|{job_type}"
        for key, value in kwargs.items():
            message += f"|{key}={value}"
        
        response = self.send_message(message)
        
        if response.startswith('OK|'):
            job_id = response.split('|')[1]
            print(f"[✓] Job submitted: {job_id} (type: {job_type}, params: {kwargs})")
            return job_id
        else:
            print(f"[✗] Error: {response}")
            return None
    
    def get_result(self, job_id, max_wait=30, poll_interval=2):
        """Get result with polling"""
        print(f"\n[...] Waiting for result of {job_id}...")
        
        start_time = time.time()
        attempts = 0
        
        while time.time() - start_time < max_wait:
            attempts += 1
            message = f"GETRESULT|{job_id}"
            response = self.send_message(message)
            
            parts = response.split('|')
            if parts[0] != 'RESULT' or len(parts) < 3:
                print(f"[ERROR] Invalid response: {response}")
                return None
            
            status = parts[2]
            print(f"[Attempt {attempts}] Status: {status}")
            
            if status == 'completed' and len(parts) >= 4:
                result = parts[3]
                try:
                    result = int(result)
                except ValueError:
                    pass
                print(f"[✓] Result received: {result}\n")
                return result
            elif status == 'in_progress':
                print(f"[...] Job in progress, waiting {poll_interval}s...")
            elif status == 'pending':
                print(f"[...] Job pending, waiting {poll_interval}s...")
            
            time.sleep(poll_interval)
        
        print(f"[✗] Timeout waiting for result after {max_wait}s\n")
        return None
    
    def close(self):
        """Close connection"""
        if self.socket:
            self.socket.close()
            print("[!] Connection closed")

if __name__ == "__main__":
    SERVER_IP = '100.89.185.61'
    
    client = JobSubmitter(SERVER_IP, cert_path='cert.pem')
    client.connect()
    
    print("\n" + "="*50)
    print("DISTRIBUTED JOB QUEUE - CLIENT TEST")
    print("SSL/TLS VERIFIED + PLAIN TEXT PROTOCOL")
    print("="*50)
    
    # Test jobs
    print("\n### Test: Multiple Jobs ###")
    jobs = []
    
    jobs.append(client.submit_job('factorial', n=10))
    jobs.append(client.submit_job('fibonacci', n=10))
    jobs.append(client.submit_job('sum', limit=100))
    jobs.append(client.submit_job('prime', n=97))
    
    print("\n[...] Retrieving results...")
    for job_id in jobs:
        if job_id:
            result = client.get_result(job_id)
    
    print("\n" + "="*50)
    print("ALL TESTS COMPLETE")
    print("="*50 + "\n")
    
    client.close()