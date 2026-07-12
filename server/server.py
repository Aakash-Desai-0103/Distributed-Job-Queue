#!/usr/bin/env python3

import socket
import threading
import ssl
import time
import csv
import os
import json
from datetime import datetime
from database import JobDatabase


class JobQueueServer:
    def __init__(self):
        self.db = JobDatabase()
        self.lock = threading.Lock()

        self.worker_heartbeats = {}
        self.heartbeat_timeout = 30
        self.heartbeat_check_interval = 5

        self.performance_log = []
        self.log_file = (
            f"performance_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )

        recovered = self.db.recover_in_progress_jobs()

        if recovered:
            print(
                f"[RECOVERY] Re-queued {recovered} "
                "in-progress jobs from previous server run"
            )

    def handle_secure_connection(
        self,
        client_sock,
        address,
        context
    ):
        try:
            secure_sock = context.wrap_socket(
                client_sock,
                server_side=True
            )

            self.handle_client(
                secure_sock,
                address
            )

        except ssl.SSLError as e:
            print(
                f"[-] SSL Error with {address}: {e}"
            )

            try:
                client_sock.close()
            except Exception:
                pass

        except Exception as e:
            print(
                f"[-] Connection error with {address}: {e}"
            )

            try:
                client_sock.close()
            except Exception:
                pass

    def handle_client(self, client_socket, address):
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
                        print(
                            f"[ERROR] Processing message "
                            f"from {address}: {e}"
                        )
                        response = self.error_response(str(e))

                    response_data = (
                        json.dumps(response) + "\n"
                    ).encode("utf-8")

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
        message_type = message.get("type")

        if not message_type:
            return self.error_response(
                "Missing required field: type"
            )

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
        job_type = message.get("job_type")
        parameters = message.get("parameters", {})
        priority = message.get("priority", 3)

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
                "Invalid job type name "
                "(alphanumeric and underscore only)"
            )

        if not isinstance(parameters, dict):
            return self.error_response(
                "parameters must be a JSON object"
            )

        if not isinstance(priority, int):
            return self.error_response(
                "priority must be an integer"
            )

        if priority < 1 or priority > 5:
            return self.error_response(
                "priority must be between 1 and 5"
            )

        job_id = self.db.create_job(
            job_type,
            parameters,
            priority
        )

        print(
            f"[QUEUE] Job {job_id} "
            f"(Priority {priority}) "
            f"added "
            f"(type: {job_type}, data: {parameters})"
        )

        return self.ok_response(
            "Job submitted successfully",
            job_id
        )
    def handle_request_job(self, message):
        worker_id = message.get("worker_id")

        if not worker_id:
            return self.error_response(
                "Missing required field: worker_id"
            )

        if not isinstance(worker_id, str):
            return self.error_response(
                "worker_id must be a string"
            )

        job = self.db.assign_next_job(worker_id)

        if job is None:
            return {
                "type": "NOJOBS",
                "message": "No jobs currently available"
            }

        print(
            f"[ASSIGN] Job {job['job_id']} "
            f"(Priority {job['priority']}) "
            f"→ Worker {worker_id}"
        )

        return {
            "type": "JOB",
            "job_id": job["job_id"],
            "job_type": job["job_type"],
            "parameters": job["parameters"],
            "priority": job["priority"]
        }

    def handle_job_complete(self, message):
        job_id = message.get("job_id")
        reporting_worker = message.get("worker_id")

        if not job_id:
            return self.error_response(
                "Missing required field: job_id"
            )

        if not reporting_worker:
            return self.error_response(
                "Missing required field: worker_id"
            )

        if "result" not in message:
            return self.error_response(
                "Missing required field: result"
            )

        result = message["result"]

        job = self.db.get_job(job_id)

        if job is None:
            return self.error_response(
                f"Job {job_id} not found"
            )

        if job["status"] != "in_progress":
            return self.error_response(
                f"Job {job_id} is not in progress"
            )

        if job["worker_id"] != reporting_worker:
            return self.error_response(
                f"Job {job_id} is assigned to "
                f"{job['worker_id']}, not {reporting_worker}"
            )

        success = self.db.complete_job(
            job_id,
            reporting_worker,
            result
        )

        if not success:
            return self.error_response(
                f"Unable to complete job {job_id}"
            )

        completed_job = self.db.get_job(job_id)

        submit_time = completed_job["submit_time"]
        assign_time = completed_job["assign_time"]
        complete_time = completed_job["complete_time"]

        queue_wait = assign_time - submit_time
        execution_time = complete_time - assign_time
        total_time = complete_time - submit_time

        perf_data = {
            "job_id": job_id,
            "job_type": completed_job["job_type"],
            "worker_id": reporting_worker,
            "submit_time": submit_time,
            "assign_time": assign_time,
            "complete_time": complete_time,
            "queue_wait": queue_wait,
            "execution_time": execution_time,
            "total_time": total_time,
            "result": result
        }

        with self.lock:
            self.performance_log.append(perf_data)

        self.save_performance_metric(perf_data)

        print(
            f"[COMPLETE] Job {job_id} by {reporting_worker} | "
            f"Queue: {queue_wait:.3f}s | "
            f"Exec: {execution_time:.3f}s | "
            f"Total: {total_time:.3f}s"
        )

        return self.ok_response(
            "Job completion recorded",
            job_id
        )

    def save_performance_metric(self, perf_data):
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

        with self.lock:
            file_exists = os.path.isfile(self.log_file)

            with open(self.log_file, "a", newline="") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=fieldnames
                )

                if not file_exists:
                    writer.writeheader()

                writer.writerow(perf_data)

    def handle_get_result(self, message):
        job_id = message.get("job_id")

        if not job_id:
            return self.error_response(
                "Missing required field: job_id"
            )

        job = self.db.get_job(job_id)

        if job is None:
            return {
                "type": "RESULT",
                "job_id": job_id,
                "status": "not_found"
            }

        response = {
            "type": "RESULT",
            "job_id": job_id,
            "status": job["status"]
        }

        if job["status"] == "completed":
            response["result"] = job["result"]

        return response

    def handle_heartbeat(self, message):
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
        with self.lock:
            self.worker_heartbeats.pop(worker_id, None)

        requeued_jobs = self.db.requeue_worker_jobs(
            worker_id
        )

        if requeued_jobs:
            print(f"\n{'='*60}")
            print(
                f"[💀] WORKER FAILURE DETECTED: "
                f"{worker_id}"
            )

            print(
                f"[RE-QUEUE] Re-queuing "
                f"{len(requeued_jobs)} jobs from dead worker"
            )

            print("="*60)

            for job_id in requeued_jobs:
                job = self.db.get_job(job_id)

                if job:
                    print(
                        f"[RE-QUEUE] ✓ Job {job_id} "
                        f"({job['job_type']}) back in queue"
                    )

            print(
                f"[RE-QUEUE] Successfully re-queued "
                f"{len(requeued_jobs)} jobs"
            )

            print("="*60 + "\n")

        else:
            print(
                f"[CLEANUP] Dead worker {worker_id} "
                "had no in-progress jobs"
            )

    def start(self):
        context = ssl.SSLContext(
            ssl.PROTOCOL_TLS_SERVER
        )

        context.load_cert_chain(
            "cert.pem",
            "key.pem"
        )

        server = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        )

        server.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1
        )

        server.bind(("0.0.0.0", 9999))
        server.listen(512)

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
        print("[*] Persistent storage: SQLite")
        print(
            f"[*] Heartbeat monitoring: ENABLED "
            f"(timeout: {self.heartbeat_timeout}s)"
        )
        print(f"[*] Performance logging: {self.log_file}")
        print("[*] Connection backlog: 512")
        print("[*] Concurrent TLS handshakes: ENABLED")
        print("[*] Ready to accept secure connections")
        print("[*] Press Ctrl+C to stop")
        print("="*60 + "\n")

        try:
            while True:
                client_sock, address = server.accept()

                thread = threading.Thread(
                    target=self.handle_secure_connection,
                    args=(
                        client_sock,
                        address,
                        context
                    ),
                    daemon=True
                )

                thread.start()

        except KeyboardInterrupt:
            print("\n[!] Server shutting down...")

            statistics = self.db.get_statistics()

            print(
                f"[!] Performance log saved: "
                f"{self.log_file}"
            )

            print(
                f"[!] Database statistics: {statistics}"
            )

        finally:
            server.close()


if __name__ == "__main__":
    server = JobQueueServer()
    server.start()
