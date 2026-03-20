import socket
import time
import ssl

class JobSubmitter:
    def __init__(self, server_host, server_port=9999):
        self.server_host = server_host
        self.server_port = server_port
        self.socket = None
    
    def connect(self):
        """Connect to server WITH SSL"""
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket = context.wrap_socket(sock, server_hostname=self.server_host)
        self.socket.connect((self.server_host, self.server_port))
        
        print(f"[+] Connected to server {self.server_host}:{self.server_port} (SSL/TLS)")
        print(f"[+] Using PLAIN TEXT protocol")
    
    def send_message(self, message):
        """Send message and get response"""
        self.socket.send((message + "\n").encode())
        
        # Read response
        buffer = ""
        while "\n" not in buffer:
            chunk = self.socket.recv(4096).decode()
            if not chunk:
                raise ConnectionError("Server closed connection")
            buffer += chunk
        
        line, _ = buffer.split("\n", 1)
        return line.strip()
    
    def submit_job(self, job_type, **kwargs):
        """Submit a job and return job_id
        Example: submit_job('factorial', n=10)
        """
        # Build message: SUBMIT_JOB|job_type|param=value|param=value
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
            
            # Parse response: RESULT|job_id|status|result
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
    SERVER_IP = '10.20.255.155'
    
    client = JobSubmitter(SERVER_IP)
    client.connect()
    
    print("\n" + "="*50)
    print("DISTRIBUTED JOB QUEUE - CLIENT TEST (SSL + PLAIN TEXT)")
    print("="*50)
    
    # Test 1: Single job
    print("\n### Test 1: Single Factorial Job ###")
    job_id = client.submit_job('factorial', n=10)
    if job_id:
        result = client.get_result(job_id)
    
    # Test 2: Multiple jobs
    print("\n### Test 2: Multiple Jobs ###")
    jobs = []
    
    jobs.append(client.submit_job('factorial', n=5))
    jobs.append(client.submit_job('fibonacci', n=10))
    jobs.append(client.submit_job('sum', limit=100))
    
    print("\n[...] Retrieving results for all jobs...")
    for job_id in jobs:
        if job_id:
            result = client.get_result(job_id)
    
    print("\n" + "="*50)
    print("ALL TESTS COMPLETE")
    print("="*50 + "\n")
    
    client.close()
