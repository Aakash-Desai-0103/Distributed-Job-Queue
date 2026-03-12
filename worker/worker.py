import socket
import json
import math
import time
import ssl

class Worker:
    def __init__(self, worker_id, server_host, server_port=9999):
        self.worker_id = worker_id
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
        
        print(f"[+] Worker {self.worker_id} connected to server {self.server_host}:{self.server_port} (SSL/TLS)")
    
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
    
    def request_job(self):
        """Request next job from server"""
        message = {
            'type': 'REQUEST_JOB',
            'worker_id': self.worker_id
        }
        
        return self.send_message(message)
    
    def send_result(self, job_id, result):
        """Send job result back to server"""
        message = {
            'type': 'JOB_COMPLETE',
            'job_id': job_id,
            'result': result
        }
        
        response = self.send_message(message)
        
        if response['status'] == 'success':
            print(f"[✓] Result sent for {job_id}")
        else:
            print(f"[✗] Failed to send result: {response.get('message')}")
    
    def execute_job(self, job):
        """Execute the job and return result"""
        job_id = job['job_id']
        job_type = job['job_type']
        data = job['data']
        
        print(f"[EXEC] Executing {job_id} (type: {job_type}, data: {data})")
        
        try:
            if job_type == 'factorial':
                n = data['n']
                result = math.factorial(n)
                print(f"[RESULT] factorial({n}) = {result}")
                return result
            
            elif job_type == 'fibonacci':
                n = data['n']
                a, b = 0, 1
                for _ in range(n):
                    a, b = b, a + b
                print(f"[RESULT] fibonacci({n}) = {a}")
                return a
            
            elif job_type == 'sleep':
                duration = data.get('duration', 2)
                print(f"[EXEC] Sleeping for {duration}s...")
                time.sleep(duration)
                print(f"[RESULT] Slept for {duration}s")
                return f"Slept {duration}s"
            
            elif job_type == 'sum':
                limit = data.get('limit', 100)
                result = sum(range(1, limit + 1))
                print(f"[RESULT] sum(1..{limit}) = {result}")
                return result
            
            else:
                print(f"[ERROR] Unknown job type: {job_type}")
                return {'error': f'Unknown job type: {job_type}'}
                
        except Exception as e:
            print(f"[ERROR] Execution failed: {e}")
            return {'error': str(e)}
    
    def work(self):
        """Main worker loop"""
        print(f"[*] Worker {self.worker_id} ready")
        print(f"[*] Starting work loop...")
        
        try:
            while True:
                # Request job
                print(f"[REQ] Requesting job from server...")
                response = self.request_job()
                
                if response['status'] == 'success':
                    job = response['job']
                    print(f"[GOT] Received job: {job['job_id']}")
                    
                    # Execute job
                    result = self.execute_job(job)
                    
                    # Send result back to server
                    self.send_result(job['job_id'], result)
                
                elif response['status'] == 'no_jobs':
                    print("[.] No jobs available, waiting 2s...")
                    time.sleep(2)
                
                else:
                    print(f"[ERROR] Unexpected response: {response}")
                    time.sleep(5)
                    
        except KeyboardInterrupt:
            print(f"\n[!] Worker {self.worker_id} shutting down...")
        except Exception as e:
            print(f"[ERROR] Worker crashed: {e}")
        finally:
            if self.socket:
                self.socket.close()

if __name__ == "__main__":
    SERVER_IP = '100.89.185.61'  # Replace with your server's Tailscale IP
    
    worker = Worker('worker_1', SERVER_IP)
    worker.connect()
    worker.work()