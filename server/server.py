import socket
import threading
import json
import queue

class JobQueueServer:
    def __init__(self):
        self.job_queue = queue.Queue()  # Thread-safe FIFO
        self.job_counter = 0
        
    def handle_client(self, client_socket, address):
        """Handle one client connection"""
        print(f"[+] Connected: {address}")
        
        try:
            while True:
                data = client_socket.recv(4096)
                if not data:
                    break
                    
                message = json.loads(data.decode())
                msg_type = message['type']
                
                if msg_type == 'SUBMIT_JOB':
                    response = self.handle_submit_job(message)
                elif msg_type == 'REQUEST_JOB':
                    response = self.handle_request_job(message)
                else:
                    response = {'status': 'error', 'message': 'Unknown type'}
                
                client_socket.send(json.dumps(response).encode())
                
        except Exception as e:
            print(f"[-] Error: {e}")
        finally:
            client_socket.close()
            print(f"[-] Disconnected: {address}")
    
    def handle_submit_job(self, message):
        """Add job to queue"""
        self.job_counter += 1
        job_id = f"job_{self.job_counter}"
        
        job = {
            'job_id': job_id,
            'job_type': message['job_type'],
            'data': message['data']
        }
        
        self.job_queue.put(job)
        print(f"[QUEUE] Job {job_id} added (type: {message['job_type']})")
        
        return {'status': 'success', 'job_id': job_id}
    
    def handle_request_job(self, message):
        """Assign job to worker"""
        worker_id = message.get('worker_id', 'unknown')
        
        try:
            job = self.job_queue.get(block=False)  # Non-blocking
            print(f"[ASSIGN] Job {job['job_id']} → Worker {worker_id}")
            return {'status': 'success', 'job': job}
        except queue.Empty:
            return {'status': 'no_jobs'}
    
    def start(self):
        """Start server"""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', 9999))
        server.listen(5)
        
        print(f"[*] Server listening on port 9999")
        
        while True:
            client_sock, address = server.accept()
            thread = threading.Thread(
                target=self.handle_client, 
                args=(client_sock, address)
            )
            thread.start()

if __name__ == "__main__":
    server = JobQueueServer()
    server.start()