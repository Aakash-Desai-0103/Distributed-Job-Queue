import socket
import threading
import queue
import ssl

class JobQueueServer:
    def __init__(self):
        self.pending_jobs = queue.Queue()
        self.assigned_jobs = {}
        self.completed_jobs = {}
        self.job_counter = 0
        self.lock = threading.Lock()
    
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
        else:
            return f"ERROR|Unknown command: {cmd}"
    
    def handle_submit_job(self, parts):
        """Add job to pending queue
        Format: SUBMIT_JOB|job_type|param=value|param=value
        Example: SUBMIT_JOB|factorial|n=10
        """
        if len(parts) < 2:
            return "ERROR|Invalid SUBMIT_JOB format"
        
        job_type = parts[1]
        
        # Parse parameters
        data = {}
        for i in range(2, len(parts)):
            if '=' in parts[i]:
                key, value = parts[i].split('=', 1)
                # Try to convert to int if possible
                try:
                    data[key] = int(value)
                except ValueError:
                    data[key] = value
        
        with self.lock:
            self.job_counter += 1
            job_id = f"job_{self.job_counter}"
        
        job = {
            'job_id': job_id,
            'job_type': job_type,
            'data': data
        }
        
        self.pending_jobs.put(job)
        print(f"[QUEUE] Job {job_id} added (type: {job_type}, data: {data})")
        
        return f"OK|{job_id}"
    
    def handle_request_job(self, parts):
        """Assign job to worker
        Format: REQUEST_JOB|worker_id
        """
        if len(parts) < 2:
            return "ERROR|Invalid REQUEST_JOB format"
        
        worker_id = parts[1]
        
        try:
            job = self.pending_jobs.get(block=False)
            
            with self.lock:
                self.assigned_jobs[job['job_id']] = worker_id
            
            print(f"[ASSIGN] Job {job['job_id']} → Worker {worker_id}")
            
            # Build response: JOB|job_id|job_type|param=value|param=value
            response = f"JOB|{job['job_id']}|{job['job_type']}"
            for key, value in job['data'].items():
                response += f"|{key}={value}"
            
            return response
            
        except queue.Empty:
            return "NOJOBS"
    
    def handle_job_complete(self, parts):
        """Store completed job result
        Format: COMPLETE|job_id|result
        """
        if len(parts) < 3:
            return "ERROR|Invalid COMPLETE format"
        
        job_id = parts[1]
        result = parts[2]
        
        # Try to convert result to int if possible
        try:
            result = int(result)
        except ValueError:
            pass
        
        with self.lock:
            if job_id in self.assigned_jobs:
                worker_id = self.assigned_jobs[job_id]
                del self.assigned_jobs[job_id]
                print(f"[COMPLETE] Job {job_id} completed by {worker_id}")
            
            self.completed_jobs[job_id] = result
            print(f"[STORED] Result for {job_id}: {result}")
        
        return "OK"
    
    def handle_get_result(self, parts):
        """Return result if available
        Format: GETRESULT|job_id
        """
        if len(parts) < 2:
            return "ERROR|Invalid GETRESULT format"
        
        job_id = parts[1]
        
        with self.lock:
            if job_id in self.completed_jobs:
                result = self.completed_jobs[job_id]
                print(f"[RESULT] Returning result for {job_id}")
                return f"RESULT|{job_id}|completed|{result}"
            elif job_id in self.assigned_jobs:
                print(f"[RESULT] Job {job_id} in progress")
                return f"RESULT|{job_id}|in_progress"
            else:
                print(f"[RESULT] Job {job_id} pending")
                return f"RESULT|{job_id}|pending"
    
    def start(self):
        """Start server WITH SSL"""
        # Create SSL context
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain('cert.pem', 'key.pem')
        
        # Create regular socket
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', 9999))
        server.listen(10)
        
        print(f"[*] Server listening on port 9999 with SSL/TLS")
        print(f"[*] Using PLAIN TEXT protocol (pipe-delimited)")
        print(f"[*] Ready to accept secure connections")
        print(f"[*] Press Ctrl+C to stop")
        
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
            server.close()

if __name__ == "__main__":
    server = JobQueueServer()
    server.start()