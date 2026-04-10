# server/server.py - FINAL VERSION FOR DELIVERABLE 2
# Handles all edge cases including whitespace and long commands

import socket
import threading
import queue
import ssl
import time
import csv
import os
from datetime import datetime

class JobQueueServer:
    def __init__(self):
        self.pending_jobs = queue.Queue()
        self.assigned_jobs = {}  # {job_id: {worker_id, assign_time, submit_time, job_type}}
        self.completed_jobs = {}  # {job_id: result}
        self.job_counter = 0
        self.lock = threading.Lock()
        
        # HEARTBEAT MONITORING
        self.worker_heartbeats = {}  # {worker_id: last_heartbeat_timestamp}
        self.worker_jobs = {}  # {worker_id: [job_ids]}
        self.heartbeat_timeout = 30  # seconds
        self.heartbeat_check_interval = 5  # check every 5 seconds
        
        # PERFORMANCE TRACKING
        self.performance_log = []
        self.log_file = f"performance_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # JOB DETAILS STORAGE (FOR RE-SCHEDULING)
        self.job_details = {}  # {job_id: {job_type, data, submit_time}}
    
    def handle_client(self, client_socket, address):
        """Handle one client connection"""
        print(f"[+] Connected: {address}")
        
        try:
            buffer = ""
            while True:
                data = client_socket.recv(4096).decode()
                if not data:
                    break
                
                buffer += data
                
                # Process complete messages (ending with \n)
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    
                    # Handle whitespace-only messages
                    if line and not line.strip():
                        client_socket.send("ERROR|Invalid message\n".encode())
                        continue
                    
                    if line.strip():
                        try:
                            response = self.route_message(line.strip())
                            client_socket.send((response + "\n").encode())
                        except Exception as e:
                            print(f"[ERROR] Processing message: {e}")
                            client_socket.send(f"ERROR|{str(e)}\n".encode())
                        
        except Exception as e:
            print(f"[-] Error with {address}: {e}")
        finally:
            client_socket.close()
            print(f"[-] Disconnected: {address}")
    
    def route_message(self, message):
        """Route message to appropriate handler"""
        parts = message.split('|')
        if not parts:
            return "ERROR|Invalid message"
        
        cmd = parts[0]
        
        if cmd == 'SUBMIT_JOB':
            return self.handle_submit_job(parts)
        elif cmd == 'REQUEST_JOB':
            return self.handle_request_job(parts)
        elif cmd == 'COMPLETE':
            return self.handle_job_complete(parts)
        elif cmd == 'GETRESULT':
            return self.handle_get_result(parts)
        elif cmd == 'HEARTBEAT':
            return self.handle_heartbeat(parts)
        else:
            return f"ERROR|Unknown command: {cmd}"
    
    def handle_submit_job(self, parts):
        """Add job to pending queue - WITH VALIDATION AND PERFORMANCE TRACKING"""
        if len(parts) < 2:
            return "ERROR|Invalid SUBMIT_JOB format"
        
        job_type = parts[1]
        
        # Validate job type length
        if len(job_type) > 50:
            return "ERROR|Job type name too long (max 50 characters)"
        
        # Validate job type contains only valid characters
        if not job_type.replace('_', '').isalnum():
            return "ERROR|Invalid job type name (alphanumeric and underscore only)"
        
        # Parse parameters
        data = {}
        for i in range(2, len(parts)):
            if '=' in parts[i]:
                key, value = parts[i].split('=', 1)
                try:
                    data[key] = int(value)
                except ValueError:
                    data[key] = value
        
        with self.lock:
            self.job_counter += 1
            job_id = f"job_{self.job_counter}"
        
        submit_time = time.time()
        
        job = {
            'job_id': job_id,
            'job_type': job_type,
            'data': data,
            'submit_time': submit_time
        }
        
        # STORE JOB DETAILS FOR RE-SCHEDULING
        with self.lock:
            self.job_details[job_id] = {
                'job_type': job_type,
                'data': data,
                'submit_time': submit_time
            }
        
        self.pending_jobs.put(job)
        print(f"[QUEUE] Job {job_id} added (type: {job_type}, data: {data})")
        
        return f"OK|{job_id}"
    
    def handle_request_job(self, parts):
        """Assign job to worker - WITH PERFORMANCE TRACKING"""
        if len(parts) < 2:
            return "ERROR|Invalid REQUEST_JOB format"
        
        worker_id = parts[1]
        
        try:
            job = self.pending_jobs.get(block=False)
            
            assign_time = time.time()
            
            with self.lock:
                self.assigned_jobs[job['job_id']] = {
                    'worker_id': worker_id,
                    'assign_time': assign_time,
                    'submit_time': job.get('submit_time', assign_time),
                    'job_type': job['job_type']
                }
                
                # Track which jobs this worker has
                if worker_id not in self.worker_jobs:
                    self.worker_jobs[worker_id] = []
                self.worker_jobs[worker_id].append(job['job_id'])
            
            print(f"[ASSIGN] Job {job['job_id']} → Worker {worker_id}")
            
            # Build response: JOB|job_id|job_type|param=value|param=value
            response = f"JOB|{job['job_id']}|{job['job_type']}"
            for key, value in job['data'].items():
                response += f"|{key}={value}"
            
            return response
            
        except queue.Empty:
            return "NOJOBS"
    
    def handle_job_complete(self, parts):
        """Store completed job result - WITH PERFORMANCE TRACKING"""
        if len(parts) < 3:
            return "ERROR|Invalid COMPLETE format"
        
        job_id = parts[1]
        result = parts[2]
        
        try:
            result = int(result)
        except ValueError:
            pass
        
        complete_time = time.time()
        
        with self.lock:
            worker_id = None
            job_info = None
            
            if job_id in self.assigned_jobs:
                job_info = self.assigned_jobs[job_id]
                worker_id = job_info['worker_id']
                
                # CALCULATE PERFORMANCE METRICS
                submit_time = job_info['submit_time']
                assign_time = job_info['assign_time']
                job_type = job_info['job_type']
                
                queue_wait = assign_time - submit_time
                execution_time = complete_time - assign_time
                total_time = complete_time - submit_time
                
                # LOG PERFORMANCE
                perf_data = {
                    'job_id': job_id,
                    'job_type': job_type,
                    'worker_id': worker_id,
                    'submit_time': submit_time,
                    'assign_time': assign_time,
                    'complete_time': complete_time,
                    'queue_wait': queue_wait,
                    'execution_time': execution_time,
                    'total_time': total_time,
                    'result': result
                }
                
                self.performance_log.append(perf_data)
                self.save_performance_metric(perf_data)
                
                print(f"[COMPLETE] Job {job_id} by {worker_id} | "
                      f"Queue: {queue_wait:.3f}s | Exec: {execution_time:.3f}s | Total: {total_time:.3f}s")
                
                del self.assigned_jobs[job_id]
                
                # Remove from worker's job list
                if worker_id in self.worker_jobs:
                    if job_id in self.worker_jobs[worker_id]:
                        self.worker_jobs[worker_id].remove(job_id)
            
            self.completed_jobs[job_id] = result
            
            # CLEAN UP JOB DETAILS
            if job_id in self.job_details:
                del self.job_details[job_id]
        
        return "OK"
    
    def save_performance_metric(self, perf_data):
        """Save performance metric to CSV"""
        file_exists = os.path.isfile(self.log_file)
        
        with open(self.log_file, 'a', newline='') as f:
            fieldnames = ['job_id', 'job_type', 'worker_id', 'submit_time', 
                          'assign_time', 'complete_time', 'queue_wait', 
                          'execution_time', 'total_time', 'result']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            if not file_exists:
                writer.writeheader()
            
            writer.writerow(perf_data)
    
    def handle_get_result(self, parts):
        """Return result if available"""
        if len(parts) < 2:
            return "ERROR|Invalid GETRESULT format"
        
        job_id = parts[1]
        
        with self.lock:
            if job_id in self.completed_jobs:
                result = self.completed_jobs[job_id]
                return f"RESULT|{job_id}|completed|{result}"
            elif job_id in self.assigned_jobs:
                return f"RESULT|{job_id}|in_progress"
            else:
                return f"RESULT|{job_id}|pending"
    
    def handle_heartbeat(self, parts):
        """Handle heartbeat from worker"""
        if len(parts) < 2:
            return "ERROR|Invalid HEARTBEAT format"
        
        worker_id = parts[1]
        
        with self.lock:
            self.worker_heartbeats[worker_id] = time.time()
        
        print(f"[💓] Heartbeat from {worker_id}")
        
        return "OK"
    
    def monitor_worker_health(self):
        """Background thread to monitor worker health"""
        print("[MONITOR] Worker health monitoring started")
        
        while True:
            time.sleep(self.heartbeat_check_interval)
            
            current_time = time.time()
            dead_workers = []
            
            with self.lock:
                # Check each worker's last heartbeat
                for worker_id, last_heartbeat in list(self.worker_heartbeats.items()):
                    time_since_heartbeat = current_time - last_heartbeat
                    
                    if time_since_heartbeat > self.heartbeat_timeout:
                        print(f"[💀] Worker {worker_id} DEAD (no heartbeat for {time_since_heartbeat:.1f}s)")
                        dead_workers.append(worker_id)
            
            # Handle dead workers
            for worker_id in dead_workers:
                self.handle_dead_worker(worker_id)
    
    def handle_dead_worker(self, worker_id):
        """Re-queue jobs from dead worker - COMPLETE IMPLEMENTATION"""
        with self.lock:
            # Remove worker from tracking
            if worker_id in self.worker_heartbeats:
                del self.worker_heartbeats[worker_id]
            
            # Get jobs assigned to this worker
            jobs_to_requeue = []
            
            # Find jobs in assigned_jobs
            for job_id, job_info in list(self.assigned_jobs.items()):
                if job_info['worker_id'] == worker_id:
                    jobs_to_requeue.append(job_id)
                    del self.assigned_jobs[job_id]
            
            # Clean up worker_jobs tracking
            if worker_id in self.worker_jobs:
                del self.worker_jobs[worker_id]
            
            # RE-QUEUE THE JOBS - COMPLETE IMPLEMENTATION
            if jobs_to_requeue:
                print(f"\n{'='*60}")
                print(f"[💀] WORKER FAILURE DETECTED: {worker_id}")
                print(f"[RE-QUEUE] Re-queuing {len(jobs_to_requeue)} jobs from dead worker")
                print(f"{'='*60}")
                
                requeued_count = 0
                for job_id in jobs_to_requeue:
                    # Get original job details
                    if job_id in self.job_details:
                        job_detail = self.job_details[job_id]
                        
                        # Reconstruct job object
                        job = {
                            'job_id': job_id,
                            'job_type': job_detail['job_type'],
                            'data': job_detail['data'],
                            'submit_time': job_detail['submit_time']
                        }
                        
                        # Put back into pending queue
                        self.pending_jobs.put(job)
                        requeued_count += 1
                        
                        print(f"[RE-QUEUE] ✓ Job {job_id} ({job_detail['job_type']}) back in queue")
                    else:
                        print(f"[RE-QUEUE] ✗ Job {job_id} details not found (skipped)")
                
                print(f"[RE-QUEUE] Successfully re-queued {requeued_count}/{len(jobs_to_requeue)} jobs")
                print(f"{'='*60}\n")
            else:
                print(f"[CLEANUP] Dead worker {worker_id} had no pending jobs")
    
    def start(self):
        """Start server WITH SSL and heartbeat monitoring"""
        # Create SSL context
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain('cert.pem', 'key.pem')
        
        # Create regular socket
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', 9999))
        server.listen(10)
        
        # Start heartbeat monitoring thread
        monitor_thread = threading.Thread(
            target=self.monitor_worker_health,
            daemon=True
        )
        monitor_thread.start()
        
        print(f"\n{'='*60}")
        print(f"[*] DISTRIBUTED JOB QUEUE SERVER - DELIVERABLE 2")
        print(f"{'='*60}")
        print(f"[*] Server listening on port 9999 with SSL/TLS")
        print(f"[*] Protocol: Plain text (pipe-delimited)")
        print(f"[*] Heartbeat monitoring: ENABLED (timeout: {self.heartbeat_timeout}s)")
        print(f"[*] Performance logging: {self.log_file}")
        print(f"[*] Ready to accept secure connections")
        print(f"[*] Press Ctrl+C to stop")
        print(f"{'='*60}\n")
        
        try:
            while True:
                client_sock, address = server.accept()
                
                # Wrap socket with SSL
                try:
                    secure_sock = context.wrap_socket(client_sock, server_side=True)
                    thread = threading.Thread(
                        target=self.handle_client,
                        args=(secure_sock, address),
                        daemon=True
                    )
                    thread.start()
                except ssl.SSLError as e:
                    print(f"[-] SSL Error with {address}: {e}")
                    client_sock.close()
                    
        except KeyboardInterrupt:
            print("\n[!] Server shutting down...")
            print(f"[!] Performance log saved: {self.log_file}")
            print(f"[!] Total jobs processed: {self.job_counter}")
            server.close()

if __name__ == "__main__":
    server = JobQueueServer()
    server.start()
