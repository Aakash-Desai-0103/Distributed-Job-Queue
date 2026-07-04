#!/usr/bin/env python3
# server/server.py - Secure Distributed Job Queue Server

import socket
import threading
import queue
import ssl
import time
import csv
import os
import json
from datetime import datetime


class JobQueueServer:
    def __init__(self):
        self.pending_jobs = queue.Queue()
        self.assigned_jobs = {}
        self.completed_jobs = {}
        self.job_details = {}
        self.job_counter = 0
        self.lock = threading.Lock()

        self.worker_heartbeats = {}
        self.worker_jobs = {}
        self.heartbeat_timeout = 30
        self.heartbeat_check_interval = 5

        self.performance_log = []
        self.log_file = (
            f"performance_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )

    def handle_client(self, client_socket, address):
        """Handle one persistent SSL/TLS connection using newline-delimited JSON"""
        print(f"[+] Connected: {address}")
        buffer = ""

        try:
            while True:
                data = client_socket.recv(4096)
                if not data:
                    break

                buffer += data.decode("utf-8")

                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)

                    if not line.strip():
                        continue

                    try:
                        message = json.loads(line)

                        if not isinstance(message, dict):
                            response = self.error_response(
                                "Message must be a JSON object"
                            )
                        else:
                            response = self.route_message(message)

                    except json.JSONDecodeError as e:
                        response = self.error_response(
                            f"Invalid JSON: {e.msg}"
                        )

                    except Exception as e:
                        print(f"[ERROR] Processing message from {address}: {e}")
                        response = self.error_response(str(e))

                    response_data = (json.dumps(response) + "\n").encode("utf-8")
                    client_socket.sendall(response_data)

        except Exception as e:
            print(f"[-] Error with {address}: {e}")

        finally:
            try:
                client_socket.close()
            except Exception:
                pass

            print(f"[-] Disconnected: {address}")

    def error_response(self, message):
        return {
            "type": "ERROR",
            "message": message
        }

    def ok_response(self, message, job_id=None):
        response = {
            "type": "OK",
            "message": message
        }

        if job_id is not None:
            response["job_id"] = job_id

        return response

    def route_message(self, message):
        """Route incoming JSON message to its handler"""
        message_type = message.get("type")

        if not message_type:
            return self.error_response("Missing required field: type")

        handlers = {
            "SUBMIT_JOB": self.handle_submit_job,
            "REQUEST_JOB": self.handle_request_job,
            "COMPLETE": self.handle_job_complete,
            "GETRESULT": self.handle_get_result,
            "HEARTBEAT": self.handle_heartbeat
        }

        handler = handlers.get(message_type)

        if handler:
            return handler(message)

        return self.error_response(
            f"Unknown message type: {message_type}"
        )

    def handle_submit_job(self, message):
        """Add a submitted job to the pending queue"""
        job_type = message.get("job_type")
        parameters = message.get("parameters", {})

        if not job_type:
            return self.error_response(
                "Missing required field: job_type"
            )

        if not isinstance(job_type, str):
            return self.error_response(
                "job_type must be a string"
            )

        if len(job_type) > 50:
            return self.error_response(
                "Job type name too long (max 50 characters)"
            )

        if not job_type.replace("_", "").isalnum():
            return self.error_response(
                "Invalid job type name (alphanumeric and underscore only)"
            )

        if not isinstance(parameters, dict):
            return self.error_response(
                "parameters must be a JSON object"
            )

        with self.lock:
            self.job_counter += 1
            job_id = f"job_{self.job_counter}"

        submit_time = time.time()

        job = {
            "job_id": job_id,
            "job_type": job_type,
            "data": parameters,
            "submit_time": submit_time
        }

        with self.lock:
            self.job_details[job_id] = {
                "job_type": job_type,
                "data": parameters,
                "submit_time": submit_time
            }

        self.pending_jobs.put(job)

        print(
            f"[QUEUE] Job {job_id} added "
            f"(type: {job_type}, data: {parameters})"
        )

        return self.ok_response(
            "Job submitted successfully",
            job_id
        )

    def handle_request_job(self, message):
        """Assign a pending job to a requesting worker"""
        worker_id = message.get("worker_id")

        if not worker_id:
            return self.error_response(
                "Missing required field: worker_id"
            )

        if not isinstance(worker_id, str):
            return self.error_response(
                "worker_id must be a string"
            )

        try:
            job = self.pending_jobs.get(block=False)
            assign_time = time.time()

            with self.lock:
                self.assigned_jobs[job["job_id"]] = {
                    "worker_id": worker_id,
                    "assign_time": assign_time,
                    "submit_time": job.get("submit_time", assign_time),
                    "job_type": job["job_type"]
                }

                if worker_id not in self.worker_jobs:
                    self.worker_jobs[worker_id] = []

                self.worker_jobs[worker_id].append(job["job_id"])

            print(
                f"[ASSIGN] Job {job['job_id']} → Worker {worker_id}"
            )

            return {
                "type": "JOB",
                "job_id": job["job_id"],
                "job_type": job["job_type"],
                "parameters": job["data"]
            }

        except queue.Empty:
            return {
                "type": "NOJOBS",
                "message": "No jobs currently available"
            }

    def handle_job_complete(self, message):
        """Record job completion and performance metrics"""
        job_id = message.get("job_id")
        reporting_worker = message.get("worker_id")

        if not job_id:
            return self.error_response(
                "Missing required field: job_id"
            )

        if "result" not in message:
            return self.error_response(
                "Missing required field: result"
            )

        result = message["result"]
        complete_time = time.time()

        with self.lock:
            if job_id in self.assigned_jobs:
                job_info = self.assigned_jobs[job_id]
                worker_id = job_info["worker_id"]

                if (
                    reporting_worker is not None
                    and reporting_worker != worker_id
                ):
                    return self.error_response(
                        f"Job {job_id} is assigned to "
                        f"{worker_id}, not {reporting_worker}"
                    )

                submit_time = job_info["submit_time"]
                assign_time = job_info["assign_time"]
                job_type = job_info["job_type"]

                queue_wait = assign_time - submit_time
                execution_time = complete_time - assign_time
                total_time = complete_time - submit_time

                perf_data = {
                    "job_id": job_id,
                    "job_type": job_type,
                    "worker_id": worker_id,
                    "submit_time": submit_time,
                    "assign_time": assign_time,
                    "complete_time": complete_time,
                    "queue_wait": queue_wait,
                    "execution_time": execution_time,
                    "total_time": total_time,
                    "result": result
                }

                self.performance_log.append(perf_data)
                self.save_performance_metric(perf_data)

                print(
                    f"[COMPLETE] Job {job_id} by {worker_id} | "
                    f"Queue: {queue_wait:.3f}s | "
                    f"Exec: {execution_time:.3f}s | "
                    f"Total: {total_time:.3f}s"
                )

                del self.assigned_jobs[job_id]

                if (
                    worker_id in self.worker_jobs
                    and job_id in self.worker_jobs[worker_id]
                ):
                    self.worker_jobs[worker_id].remove(job_id)

            self.completed_jobs[job_id] = result
            self.job_details.pop(job_id, None)

        return self.ok_response(
            "Job completion recorded",
            job_id
        )

    def save_performance_metric(self, perf_data):
        """Append completed job performance data to CSV"""
        file_exists = os.path.isfile(self.log_file)

        fieldnames = [
            "job_id",
            "job_type",
            "worker_id",
            "submit_time",
            "assign_time",
            "complete_time",
            "queue_wait",
            "execution_time",
            "total_time",
            "result"
        ]

        with open(self.log_file, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)

            if not file_exists:
                writer.writeheader()

            writer.writerow(perf_data)

    def handle_get_result(self, message):
        """Return current job status or completed result"""
        job_id = message.get("job_id")

        if not job_id:
            return self.error_response(
                "Missing required field: job_id"
            )

        with self.lock:
            if job_id in self.completed_jobs:
                return {
                    "type": "RESULT",
                    "job_id": job_id,
                    "status": "completed",
                    "result": self.completed_jobs[job_id]
                }

            if job_id in self.assigned_jobs:
                return {
                    "type": "RESULT",
                    "job_id": job_id,
                    "status": "in_progress"
                }

            if job_id in self.job_details:
                return {
                    "type": "RESULT",
                    "job_id": job_id,
                    "status": "pending"
                }

            return {
                "type": "RESULT",
                "job_id": job_id,
                "status": "not_found"
            }

    def handle_heartbeat(self, message):
        """Update worker heartbeat timestamp"""
        worker_id = message.get("worker_id")

        if not worker_id:
            return self.error_response(
                "Missing required field: worker_id"
            )

        with self.lock:
            self.worker_heartbeats[worker_id] = time.time()

        print(f"[💓] Heartbeat from {worker_id}")

        return self.ok_response(
            "Heartbeat acknowledged"
        )

    def monitor_worker_health(self):
        """Detect workers that stop sending heartbeats"""
        print("[MONITOR] Worker health monitoring started")

        while True:
            time.sleep(self.heartbeat_check_interval)
            current_time = time.time()
            dead_workers = []

            with self.lock:
                for worker_id, last_heartbeat in list(
                    self.worker_heartbeats.items()
                ):
                    elapsed = current_time - last_heartbeat

                    if elapsed > self.heartbeat_timeout:
                        print(
                            f"[💀] Worker {worker_id} DEAD "
                            f"(no heartbeat for {elapsed:.1f}s)"
                        )
                        dead_workers.append(worker_id)

            for worker_id in dead_workers:
                self.handle_dead_worker(worker_id)

    def handle_dead_worker(self, worker_id):
        """Re-queue unfinished jobs assigned to a dead worker"""
        with self.lock:
            self.worker_heartbeats.pop(worker_id, None)

            jobs_to_requeue = []

            for job_id, job_info in list(self.assigned_jobs.items()):
                if job_info["worker_id"] == worker_id:
                    jobs_to_requeue.append(job_id)
                    del self.assigned_jobs[job_id]

            self.worker_jobs.pop(worker_id, None)

            reconstructed_jobs = []

            for job_id in jobs_to_requeue:
                if job_id in self.job_details:
                    details = self.job_details[job_id]

                    reconstructed_jobs.append({
                        "job_id": job_id,
                        "job_type": details["job_type"],
                        "data": details["data"],
                        "submit_time": details["submit_time"]
                    })

        if jobs_to_requeue:
            print(f"\n{'='*60}")
            print(f"[💀] WORKER FAILURE DETECTED: {worker_id}")
            print(
                f"[RE-QUEUE] Re-queuing "
                f"{len(jobs_to_requeue)} jobs from dead worker"
            )
            print("="*60)

            for job in reconstructed_jobs:
                self.pending_jobs.put(job)
                print(
                    f"[RE-QUEUE] ✓ Job {job['job_id']} "
                    f"({job['job_type']}) back in queue"
                )

            print(
                f"[RE-QUEUE] Successfully re-queued "
                f"{len(reconstructed_jobs)}/{len(jobs_to_requeue)} jobs"
            )
            print("="*60 + "\n")

        else:
            print(
                f"[CLEANUP] Dead worker {worker_id} had no pending jobs"
            )

    def start(self):
        """Start the TLS server and heartbeat monitor"""
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain("cert.pem", "key.pem")

        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("0.0.0.0", 9999))
        server.listen(10)

        monitor_thread = threading.Thread(
            target=self.monitor_worker_health,
            daemon=True
        )
        monitor_thread.start()

        print(f"\n{'='*60}")
        print("[*] SECURE DISTRIBUTED JOB QUEUE SERVER")
        print("="*60)
        print("[*] Server listening on port 9999 with SSL/TLS")
        print("[*] Protocol: Newline-delimited JSON")
        print(
            f"[*] Heartbeat monitoring: ENABLED "
            f"(timeout: {self.heartbeat_timeout}s)"
        )
        print(f"[*] Performance logging: {self.log_file}")
        print("[*] Ready to accept secure connections")
        print("[*] Press Ctrl+C to stop")
        print("="*60 + "\n")

        try:
            while True:
                client_sock, address = server.accept()

                try:
                    secure_sock = context.wrap_socket(
                        client_sock,
                        server_side=True
                    )

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
            print(f"[!] Total jobs submitted: {self.job_counter}")

        finally:
            server.close()


if __name__ == "__main__":
    server = JobQueueServer()
    server.start()
