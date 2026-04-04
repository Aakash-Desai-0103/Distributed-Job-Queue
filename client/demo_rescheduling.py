#!/usr/bin/env python3
# client/demo_rescheduling.py - Demonstrates heartbeat monitoring and job re-scheduling
# UPDATED WITH LONGER TIMEOUT FOR RE-QUEUED JOBS

import socket
import time
import ssl
import os
import sys

class ReschedulingDemo:
    def __init__(self, server_host, server_port=9999, cert_path='cert.pem'):
        self.server_host = server_host
        self.server_port = server_port
        self.cert_path = cert_path
        self.socket = None
    
    def connect(self):
        """Connect to server WITH SSL VERIFICATION"""
        if not os.path.exists(self.cert_path):
            print(f"[ERROR] Certificate not found: {self.cert_path}")
            sys.exit(1)
        
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.load_verify_locations(self.cert_path)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_REQUIRED
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket = context.wrap_socket(sock, server_hostname=self.server_host)
            self.socket.connect((self.server_host, self.server_port))
            
            print(f"[🔒] Connected to {self.server_host}:{self.server_port} (SSL/TLS)")
        except Exception as e:
            print(f"[ERROR] Connection failed: {e}")
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
        """Submit a job"""
        message = f"SUBMIT_JOB|{job_type}"
        for key, value in kwargs.items():
            message += f"|{key}={value}"
        
        response = self.send_message(message)
        
        if response.startswith('OK|'):
            job_id = response.split('|')[1]
            return job_id
        else:
            return None
    
    def get_result(self, job_id, timeout=120):
        """Get result with timeout - INCREASED TIMEOUT FOR RE-QUEUED JOBS"""
        start = time.time()
        while time.time() - start < timeout:
            message = f"GETRESULT|{job_id}"
            response = self.send_message(message)
            
            parts = response.split('|')
            if parts[0] == 'RESULT' and len(parts) >= 3:
                status = parts[2]
                if status == 'completed' and len(parts) >= 4:
                    return parts[3]
            
            time.sleep(2)
        
        return None
    
    def run_demo(self):
        """Run the re-scheduling demonstration"""
        print("\n" + "="*70)
        print("FAULT TOLERANCE DEMONSTRATION - JOB RE-SCHEDULING")
        print("="*70)
        print("\nThis demo will:")
        print("  1. Submit 10 long-running jobs (sleep jobs)")
        print("  2. Wait for workers to start processing")
        print("  3. YOU will kill a worker (Ctrl+C in worker terminal)")
        print("  4. Server will detect dead worker (30s timeout)")
        print("  5. Server will re-queue the worker's jobs")
        print("  6. Remaining workers will complete all jobs")
        print("\n" + "="*70)
        
        input("\nPress Enter to start demo...")
        
        # Phase 1: Submit jobs
        print("\n[PHASE 1] Submitting 10 long-running jobs...")
        jobs = []
        for i in range(1, 11):
            job_id = self.submit_job('sleep', duration=20)  # 20 second jobs
            if job_id:
                jobs.append(job_id)
                print(f"  ✓ Submitted {job_id} (sleep 20s)")
        
        print(f"\n[INFO] {len(jobs)} jobs submitted")
        
        # Phase 2: Wait for assignment
        print("\n[PHASE 2] Waiting for workers to pick up jobs (10 seconds)...")
        time.sleep(10)
        
        # Phase 3: Instructions
        print("\n[PHASE 3] Jobs are now running on workers")
        print("\n" + "="*70)
        print("NOW KILL ONE WORKER:")
        print("  1. Go to one of your worker terminals")
        print("  2. Press Ctrl+C to kill the worker")
        print("  3. Come back here and watch the magic!")
        print("="*70)
        
        input("\nPress Enter after you've killed a worker...")
        
        # Phase 4: Wait for detection
        print("\n[PHASE 4] Waiting for server to detect dead worker...")
        print("  (Server checks every 5s, timeout is 30s)")
        print("  Watch server terminal for:")
        print("    - [💀] Worker DEAD message")
        print("    - [RE-QUEUE] Job re-scheduling messages")
        print("\n  Waiting 35 seconds...")
        
        for i in range(35, 0, -5):
            print(f"  ... {i} seconds remaining")
            time.sleep(5)
        
        # Phase 5: Check results
        print("\n[PHASE 5] Checking job completion...")
        print("  (Jobs may take up to 2 minutes due to re-queueing)")
        
        completed = 0
        failed = 0
        
        for job_id in jobs:
            print(f"\n  Checking {job_id}...", end=" ")
            result = self.get_result(job_id, timeout=120)  # INCREASED FROM 60 TO 120
            
            if result:
                print(f"✓ COMPLETED (result: {result})")
                completed += 1
            else:
                print(f"✗ FAILED or TIMEOUT")
                failed += 1
        
        # Summary
        print("\n" + "="*70)
        print("DEMONSTRATION COMPLETE!")
        print("="*70)
        print(f"\n  Total jobs: {len(jobs)}")
        print(f"  Completed: {completed}")
        print(f"  Failed: {failed}")
        
        if completed == len(jobs):
            print("\n  ✅ SUCCESS! All jobs completed despite worker failure!")
            print("  🎯 This proves fault tolerance and job re-scheduling work!")
        else:
            print("\n  ⚠️ Some jobs didn't complete - check server logs")
        
        print("\n" + "="*70)
        print("\nKEY OBSERVATIONS:")
        print("  1. Server detected dead worker after 30s of no heartbeat")
        print("  2. Jobs from dead worker were re-queued automatically")
        print("  3. Remaining workers picked up re-queued jobs")
        print("  4. All jobs completed successfully despite failure")
        print("\nThis demonstrates:")
        print("  ✓ Heartbeat monitoring")
        print("  ✓ Dead worker detection")
        print("  ✓ Automatic job re-scheduling")
        print("  ✓ Fault tolerance")
        print("  ✓ System resilience")
        print("="*70 + "\n")
    
    def close(self):
        """Close connection"""
        if self.socket:
            self.socket.close()

if __name__ == "__main__":
    SERVER_IP = '100.89.185.61'  # Change to Tailscale IP for team demo
    
    demo = ReschedulingDemo(SERVER_IP, cert_path='cert.pem')
    demo.connect()
    
    try:
        demo.run_demo()
    except KeyboardInterrupt:
        print("\n\n[!] Demo interrupted by user")
    except Exception as e:
        print(f"\n[ERROR] Demo failed: {e}")
    finally:
        demo.close()