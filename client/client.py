import socket
import json
import time
import ssl

class JobSubmitter:
    def __init__(self, server_host, server_port=9999):
        self.server_host = server_host
        self.server_port = server_port
        self.socket = None
    
    def connect(self):
        """Connect to server WITH SSL"""
        # Create SSL context
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE  # For self-signed certs
        
        # Create socket and wrap with SSL
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket = context.wrap_socket(sock, server_hostname=self.server_host)
        self.socket.connect((self.server_host, self.server_port))
        
        print(f"[+] Connected to server {self.server_host}:{self.server_port} (SSL/TLS)")
    
    def send_message(self, message):
        """Send message and get response"""
        self.socket.send((json.dumps(message) + "\n").encode())
        
        # Read response
        buffer = ""
        while "\n" not in buffer:
            chunk = self.socket.recv(4096).decode()
            if not chunk:
                raise ConnectionError("Server closed connection")
            buffer += chunk
        
        line, _ = buffer.split("\n", 1)
        return json.loads(line)
    
    def submit_job(self, job_type, data):
        """Submit a job and return job_id"""
        message = {
            'type': 'SUBMIT_JOB',
            'job_type': job_type,
            'data': data
        }
        
        response = self.send_message(message)
        
        if response['status'] == 'success':
            job_id = response['job_id']
            print(f"[✓] Job submitted: {job_id} (type: {job_type}, data: {data})")
            return job_id
        else:
            print(f"[✗] Error: {response.get('message', 'Unknown')}")
            return None
    
    def get_result(self, job_id, max_wait=30, poll_interval=2):
        """Get result with polling"""
        print(f"\n[...] Waiting for result of {job_id}...")
        
        start_time = time.time()
        attempts = 0
        
        while time.time() - start_time < max_wait:
            attempts += 1
            message = {
                'type': 'GET_RESULT',
                'job_id': job_id
            }
            
            response = self.send_message(message)
            status = response.get('status')
            
            print(f"[Attempt {attempts}] Status: {status}")
            
            if status == 'completed':
                result = response['result']
                print(f"[✓] Result received: {result}\n")
                return result
            elif status == 'in_progress':
                print(f"[...] Job in progress, waiting {poll_interval}s...")
            elif status == 'pending':
                print(f"[...] Job pending (not yet assigned), waiting {poll_interval}s...")
            else:
                print(f"[...] Unknown status: {status}, waiting {poll_interval}s...")
            
            time.sleep(poll_interval)
        
        print(f"[✗] Timeout waiting for result after {max_wait}s\n")
        return None
    
    def close(self):
        """Close connection"""
        if self.socket:
            self.socket.close()
            print("[!] Connection closed")

if __name__ == "__main__":
    SERVER_IP = '100.89.185.61'  # Replace with your server's Tailscale IP
    
    client = JobSubmitter(SERVER_IP)
    client.connect()
    
    print("\n" + "="*50)
    print("DISTRIBUTED JOB QUEUE - CLIENT TEST (SSL)")
    print("="*50)
    
    # Test 1: Single job
    print("\n### Test 1: Single Factorial Job ###")
    job_id = client.submit_job('factorial', {'n': 10})
    if job_id:
        result = client.get_result(job_id)
    
    # Test 2: Multiple jobs
    print("\n### Test 2: Multiple Jobs ###")
    jobs = []
    
    jobs.append(client.submit_job('factorial', {'n': 5}))
    jobs.append(client.submit_job('fibonacci', {'n': 10}))
    jobs.append(client.submit_job('sum', {'limit': 100}))
    
    print("\n[...] Retrieving results for all jobs...")
    for job_id in jobs:
        if job_id:
            result = client.get_result(job_id)
    
    print("\n" + "="*50)
    print("ALL TESTS COMPLETE")
    print("="*50 + "\n")
    
    client.close()