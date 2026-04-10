#!/usr/bin/env python3
# worker/worker_crashable.py - Worker that crashes for testing

import socket
import math
import time
import ssl
import threading
import os
import sys

# CRASH CONFIGURATION
CRASH_AFTER_JOBS = 2  # Will crash after completing 2 jobs
jobs_completed = 0

class Worker:
    def __init__(self, worker_id, server_host, server_port=9999, cert_path='cert.pem'):
        self.worker_id = worker_id
        self.server_host = server_host
        self.server_port = server_port
        self.cert_path = cert_path
        self.socket = None
        self.running = True
        self.heartbeat_interval = 10
        self.socket_lock = threading.Lock()

    
    def verify_certificate_exists(self):
        """Check if certificate file exists"""
        if not os.path.exists(self.cert_path):
            print(f"[ERROR] Certificate not found: {self.cert_path}")
            print(f"[INFO] Please copy cert.pem from server to worker directory")
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
            self.socket = context.wrap_socket(sock, server_hostname=self.server_host)
            self.socket.connect((self.server_host, self.server_port))
            
            cert = self.socket.getpeercert()
            
            print(f"\n{'='*60}")
            print(f"[🔒] SSL CONNECTION ESTABLISHED")
            print(f"{'='*60}")
            print(f"[+] Worker {self.worker_id} connected to {self.server_host}:{self.server_port}")
            print(f"[🔐] SSL/TLS Protocol: {self.socket.version()}")
            print(f"[✓] Certificate verified successfully!")
            
            if cert:
                subject = dict(x[0] for x in cert['subject'])
                print(f"[📜] Certificate CN: {subject.get('commonName', 'N/A')}")
                print(f"[📅] Valid until: {cert['notAfter']}")
            
            print(f"[+] Using PLAIN TEXT protocol (pipe-delimited)")
            print(f"[💓] Heartbeat enabled: {self.heartbeat_interval}s interval")
            print(f"[💥] CRASH MODE: Will crash after {CRASH_AFTER_JOBS} jobs")
            print(f"{'='*60}\n")
            
        except Exception as e:
            print(f"\n[❌] CONNECTION FAILED!")
            print(f"[ERROR] {e}")
            sys.exit(1)
    
    def send_message(self, message):
        with self.socket_lock:
            self.socket.send((message + "\n").encode())
        
            buffer = ""
            while "\n" not in buffer:
                chunk = self.socket.recv(4096).decode()
                if not chunk:
                    raise ConnectionError("Server closed connection")
                buffer += chunk
        
            line, _ = buffer.split("\n", 1)
            return line.strip()
    
    
    def send_heartbeat(self):
        """Background thread to send periodic heartbeats"""
        print(f"[💓] Heartbeat thread started")
    
        while self.running:
            try:
                time.sleep(self.heartbeat_interval)
            
                if not self.running:
                    break
            
                message = f"HEARTBEAT|{self.worker_id}"
                response = self.send_message(message)
            
                if response == "OK":
                    print(f"[💓] Heartbeat sent → Server OK")
                else:
                    print(f"[💓] Heartbeat response: {response}")
                
            except Exception as e:
                print(f"[💓] Heartbeat failed: {e}")
                time.sleep(5)
    
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
        """Parse job from server response"""
        parts = response.split('|')
        if parts[0] != 'JOB' or len(parts) < 3:
            return None
        
        job = {
            'job_id': parts[1],
            'job_type': parts[2],
            'data': {}
        }
        
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
        global jobs_completed
        
        job_id = job['job_id']
        job_type = job['job_type']
        data = job['data']
        
        print(f"[EXEC] Executing {job_id} (type: {job_type}, data: {data})")
        
        try:
            # Execute based on job type
            if job_type == 'factorial':
                n = data.get('n', 0)
                result = math.factorial(n)
                print(f"[RESULT] factorial({n}) = {result}")
            
            elif job_type == 'fibonacci':
                n = data.get('n', 0)
                a, b = 0, 1
                for _ in range(n):
                    a, b = b, a + b
                result = a
                print(f"[RESULT] fibonacci({n}) = {a}")
            
            elif job_type == 'sleep':
                duration = data.get('duration', 2)
                print(f"[EXEC] Sleeping for {duration}s...")
                time.sleep(duration)
                result = f"Slept_{duration}s"
                print(f"[RESULT] Slept for {duration}s")
            
            elif job_type == 'sum':
                limit = data.get('limit', 100)
                result = sum(range(1, limit + 1))
                print(f"[RESULT] sum(1..{limit}) = {result}")
            
            elif job_type == 'prime':
                n = data.get('n', 2)
                result = self.is_prime(n)
                print(f"[RESULT] is_prime({n}) = {result}")
            
            elif job_type == 'power':
                x = data.get('x', 2)
                y = data.get('y', 10)
                result = x ** y
                print(f"[RESULT] {x}^{y} = {result}")
            
            elif job_type == 'gcd':
                a = data.get('a', 48)
                b = data.get('b', 18)
                result = math.gcd(a, b)
                print(f"[RESULT] gcd({a}, {b}) = {result}")
            
            elif job_type == 'sort':
                size = data.get('size', 1000)
                import random
                random.seed(size)
                arr = [random.randint(1, 10000) for _ in range(size)]
                sorted_arr = sorted(arr)
                result = len(sorted_arr)
                print(f"[RESULT] sorted {size} numbers")
            
            elif job_type == 'matrix':
                size = data.get('size', 10)
                result = self.matrix_multiply(size)
                print(f"[RESULT] matrix multiply {size}x{size}")
            
            else:
                print(f"[ERROR] Unknown job type: {job_type}")
                return f"ERROR_Unknown_job_type"
            
            # INCREMENT JOB COUNTER AND CHECK FOR CRASH
            jobs_completed += 1
            print(f"[INFO] Jobs completed: {jobs_completed}/{CRASH_AFTER_JOBS}")
            
            if jobs_completed >= CRASH_AFTER_JOBS:
                print(f"\n{'='*60}")
                print(f"[💥] SIMULATED CRASH - Completed {jobs_completed} jobs")
                print(f"[💥] This worker is now terminating to simulate failure")
                print(f"[💥] Server should detect death and re-queue unfinished jobs")
                print(f"{'='*60}\n")
                time.sleep(1)  # Brief pause for message to show
                sys.exit(1)  # SIMULATE CRASH
            
            return result
                
        except Exception as e:
            print(f"[ERROR] Execution failed: {e}")
            return f"ERROR_{str(e)}"
    
    def is_prime(self, n):
        """Check if n is prime"""
        if n < 2:
            return 0
        if n == 2:
            return 1
        if n % 2 == 0:
            return 0
        for i in range(3, int(math.sqrt(n)) + 1, 2):
            if n % i == 0:
                return 0
        return 1
    
    def matrix_multiply(self, size):
        """Simple matrix multiplication"""
        matrix_a = [[i + j for j in range(size)] for i in range(size)]
        matrix_b = [[i * j for j in range(size)] for i in range(size)]
        
        result = 0
        for i in range(size):
            for j in range(size):
                result += matrix_a[i][j] * matrix_b[i][j]
        
        return result
    
    def work(self):
        """Main worker loop"""
        print(f"[*] Worker {self.worker_id} ready")
        print(f"[*] Supporting 9 job types")
        
        heartbeat_thread = threading.Thread(
            target=self.send_heartbeat,
            daemon=True
        )
        heartbeat_thread.start()
        
        try:
            while self.running:
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
            self.running = False
        except Exception as e:
            print(f"[ERROR] Worker crashed: {e}")
            self.running = False
        finally:
            if self.socket:
                self.socket.close()

if __name__ == "__main__":
    SERVER_IP = '100.89.185.61'
    
    worker = Worker('worker_crashable', SERVER_IP, cert_path='cert.pem')
    worker.connect()
    worker.work()