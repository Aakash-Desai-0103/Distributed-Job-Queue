import socket
import threading
import json
import queue

class JobQueueServer:
    def __init__(self):
        self.pending_jobs = queue.Queue()  # Jobs waiting to be assigned
        self.assigned_jobs = {}  # {job_id: worker_id}
        self.completed_jobs = {}  # {job_id: result}
        self.job_counter = 0
        self.lock = threading.Lock()  # For thread safety
        
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
                    if line.strip():
                        try:
                            message = json.loads(line)
                            response = self.route_message(message)
                            client_socket.send((json.dumps(response) + "\n").encode())
                        except json.JSONDecodeError as e:
                            print(f"[ERROR] Invalid JSON: {e}")
                        except Exception as e:
                            print(f"[ERROR] Processing message: {e}")
                        
        except Exception as e:
            print(f"[-] Error with {address}: {e}")
        finally:
            client_socket.close()
            print(f"[-] Disconnected: {address}")
    
    def route_message(self, message):
        """Route message to appropriate handler"""
        msg_type = message.get('type')
        
        if msg_type == 'SUBMIT_JOB':
            return self.handle_submit_job(message)
        elif msg_type == 'REQUEST_JOB':
            return self.handle_request_job(message)
        elif msg_type == 'JOB_COMPLETE':
            return self.handle_job_complete(message)
        elif msg_type == 'GET_RESULT':
            return self.handle_get_result(message)
        else:
            return {'status': 'error', 'message': f'Unknown type: {msg_type}'}
    
    def handle_submit_job(self, message):
        """Add job to pending queue"""
        with self.lock:
            self.job_counter += 1
            job_id = f"job_{self.job_counter}"
        
        job = {
            'job_id': job_id,
            'job_type': message['job_type'],
            'data': message['data']
        }
        
        self.pending_jobs.put(job)
        print(f"[QUEUE] Job {job_id} added (type: {message['job_type']}, data: {message['data']})")
        
        return {'status': 'success', 'job_id': job_id}
    
    def handle_request_job(self, message):
        """Assign job to worker"""
        worker_id = message.get('worker_id', 'unknown')
        
        try:
            job = self.pending_jobs.get(block=False)
            
            with self.lock:
                self.assigned_jobs[job['job_id']] = worker_id
            
            print(f"[ASSIGN] Job {job['job_id']} → Worker {worker_id}")
            return {'status': 'success', 'job': job}
            
        except queue.Empty:
            return {'status': 'no_jobs'}
    
    def handle_job_complete(self, message):
        """Store completed job result"""
        job_id = message['job_id']
        result = message['result']
        
        with self.lock:
            # Remove from assigned
            if job_id in self.assigned_jobs:
                worker_id = self.assigned_jobs[job_id]
                del self.assigned_jobs[job_id]
                print(f"[COMPLETE] Job {job_id} completed by {worker_id}")
            
            # Store result
            self.completed_jobs[job_id] = result
            print(f"[STORED] Result for {job_id}: {result}")
        
        return {'status': 'success'}
    
    def handle_get_result(self, message):
        """Return result if available"""
        job_id = message['job_id']
        
        with self.lock:
            if job_id in self.completed_jobs:
                result = self.completed_jobs[job_id]
                print(f"[RESULT] Returning result for {job_id}")
                return {
                    'type': 'RESULT',
                    'job_id': job_id,
                    'status': 'completed',
                    'result': result
                }
            elif job_id in self.assigned_jobs:
                print(f"[RESULT] Job {job_id} in progress")
                return {
                    'type': 'RESULT',
                    'job_id': job_id,
                    'status': 'in_progress'
                }
            else:
                print(f"[RESULT] Job {job_id} pending")
                return {
                    'type': 'RESULT',
                    'job_id': job_id,
                    'status': 'pending'
                }
    
    def start(self):
        """Start server WITHOUT SSL"""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', 9999))
        server.listen(10)
        
        print(f"[*] Server listening on port 9999")
        print(f"[*] Ready to accept connections")
        print(f"[*] Press Ctrl+C to stop")
        
        try:
            while True:
                client_sock, address = server.accept()
                thread = threading.Thread(
                    target=self.handle_client, 
                    args=(client_sock, address),
                    daemon=True
                )
                thread.start()
        except KeyboardInterrupt:
            print("\n[!] Server shutting down...")
            server.close()

if __name__ == "__main__":
    server = JobQueueServer()
    server.start()