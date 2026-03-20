import socket
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
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket = context.wrap_socket(sock, server_hostname=self.server_host)
        self.socket.connect((self.server_host, self.server_port))
        
        print(f"[+] Worker {self.worker_id} connected to server (SSL/TLS)")
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
    
    def request_job(self):
        """Request next job from server"""
        message = f"REQUEST_JOB|{self.worker_id}"
        return self.send_message(message)
    
    def send_result(self, job_id, result):
        """Send job result back to server"""
        message = f"COMPLETE|{job_id}|{result}"
        response = self.send_message(message)
        
        if response == "OK":
            print(f"[✓] Result sent for {job_id}")
        else:
            print(f"[✗] Failed to send result: {response}")
    
    def parse_job(self, response):
        """Parse job from server response
        Format: JOB|job_id|job_type|param=value|param=value
        """
        parts = response.split('|')
        if parts[0] != 'JOB' or len(parts) < 3:
            return None
        
        job = {
            'job_id': parts[1],
            'job_type': parts[2],
            'data': {}
        }
        
        # Parse parameters
        for i in range(3, len(parts)):
            if '=' in parts[i]:
                key, value = parts[i].split('=', 1)
                try:
                    job['data'][key] = int(value)
                except ValueError:
                    job['data'][key] = value
        
        return job
    
    def execute_job(self, job):
        """Execute the job and return result"""
        job_id = job['job_id']
        job_type = job['job_type']
        data = job['data']
        
        print(f"[EXEC] Executing {job_id} (type: {job_type}, data: {data})")
        
        try:
            if job_type == 'factorial':
                n = data.get('n', 0)
                result = math.factorial(n)
                print(f"[RESULT] factorial({n}) = {result}")
                return result
            
            elif job_type == 'fibonacci':
                n = data.get('n', 0)
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
                return f"Slept_{duration}s"
            
            elif job_type == 'sum':
                limit = data.get('limit', 100)
                result = sum(range(1, limit + 1))
                print(f"[RESULT] sum(1..{limit}) = {result}")
                return result
            
            else:
                print(f"[ERROR] Unknown job type: {job_type}")
                return f"ERROR_Unknown_job_type"
                
        except Exception as e:
            print(f"[ERROR] Execution failed: {e}")
            return f"ERROR_{str(e)}"
    
    def work(self):
        """Main worker loop"""
        print(f"[*] Worker {self.worker_id} ready")
        print(f"[*] Starting work loop...")
        
        try:
            while True:
                print(f"[REQ] Requesting job from server...")
                response = self.request_job()
                
                if response.startswith('JOB|'):
                    job = self.parse_job(response)
                    if job:
                        print(f"[GOT] Received job: {job['job_id']}")
                        result = self.execute_job(job)
                        self.send_result(job['job_id'], result)
                
                elif response == 'NOJOBS':
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
    SERVER_IP = '10.20.255.155'
    
    worker = Worker('worker_1', SERVER_IP)
    worker.connect()
    worker.work()