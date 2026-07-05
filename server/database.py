import sqlite3
import json
import time
import threading
import os


class JobDatabase:
    def __init__(self, db_path="jobs.db"):
        self.db_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            db_path
        )
        self.lock = threading.Lock()
        self.initialize()

    def connect(self):
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self):
        with self.connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT UNIQUE,
                    job_type TEXT NOT NULL,
                    parameters TEXT NOT NULL,

                    status TEXT NOT NULL DEFAULT 'pending'
                        CHECK (
                            status IN (
                                'pending',
                                'in_progress',
                                'completed'
                            )
                        ),

                    worker_id TEXT,
                    result TEXT,

                    submit_time REAL NOT NULL,
                    assign_time REAL,
                    complete_time REAL,

                    retry_count INTEGER NOT NULL DEFAULT 0
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_jobs_status
                ON jobs(status)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_jobs_worker_id
                ON jobs(worker_id)
            """)

    def create_job(self, job_type, parameters):
        with self.lock:
            with self.connect() as conn:
                cursor = conn.execute("""
                    INSERT INTO jobs (
                        job_type,
                        parameters,
                        status,
                        submit_time
                    )
                    VALUES (?, ?, 'pending', ?)
                """, (
                    job_type,
                    json.dumps(parameters),
                    time.time()
                ))

                row_id = cursor.lastrowid
                job_id = f"job_{row_id}"

                conn.execute("""
                    UPDATE jobs
                    SET job_id = ?
                    WHERE id = ?
                """, (
                    job_id,
                    row_id
                ))

                return job_id

    def assign_next_job(self, worker_id):
        with self.lock:
            with self.connect() as conn:
                conn.execute("BEGIN IMMEDIATE")

                row = conn.execute("""
                    SELECT *
                    FROM jobs
                    WHERE status = 'pending'
                    ORDER BY id ASC
                    LIMIT 1
                """).fetchone()

                if row is None:
                    conn.commit()
                    return None

                assign_time = time.time()

                conn.execute("""
                    UPDATE jobs
                    SET status = 'in_progress',
                        worker_id = ?,
                        assign_time = ?
                    WHERE job_id = ?
                """, (
                    worker_id,
                    assign_time,
                    row["job_id"]
                ))

                conn.commit()

                return {
                    "job_id": row["job_id"],
                    "job_type": row["job_type"],
                    "parameters": json.loads(row["parameters"])
                }

    def complete_job(self, job_id, worker_id, result):
        with self.lock:
            with self.connect() as conn:
                cursor = conn.execute("""
                    UPDATE jobs
                    SET status = 'completed',
                        result = ?,
                        complete_time = ?
                    WHERE job_id = ?
                      AND worker_id = ?
                      AND status = 'in_progress'
                """, (
                    json.dumps(result),
                    time.time(),
                    job_id,
                    worker_id
                ))

                return cursor.rowcount > 0

    def get_job(self, job_id):
        with self.connect() as conn:
            row = conn.execute("""
                SELECT *
                FROM jobs
                WHERE job_id = ?
            """, (job_id,)).fetchone()

            if row is None:
                return None

            result = row["result"]

            if result is not None:
                try:
                    result = json.loads(result)
                except json.JSONDecodeError:
                    pass

            return {
                "job_id": row["job_id"],
                "job_type": row["job_type"],
                "parameters": json.loads(row["parameters"]),
                "status": row["status"],
                "worker_id": row["worker_id"],
                "result": result,
                "submit_time": row["submit_time"],
                "assign_time": row["assign_time"],
                "complete_time": row["complete_time"],
                "retry_count": row["retry_count"]
            }

    def requeue_worker_jobs(self, worker_id):
        with self.lock:
            with self.connect() as conn:
                rows = conn.execute("""
                    SELECT job_id
                    FROM jobs
                    WHERE worker_id = ?
                      AND status = 'in_progress'
                """, (worker_id,)).fetchall()

                job_ids = [
                    row["job_id"]
                    for row in rows
                ]

                conn.execute("""
                    UPDATE jobs
                    SET status = 'pending',
                        worker_id = NULL,
                        assign_time = NULL,
                        retry_count = retry_count + 1
                    WHERE worker_id = ?
                      AND status = 'in_progress'
                """, (worker_id,))

                return job_ids

    def recover_in_progress_jobs(self):
        with self.lock:
            with self.connect() as conn:
                cursor = conn.execute("""
                    UPDATE jobs
                    SET status = 'pending',
                        worker_id = NULL,
                        assign_time = NULL,
                        retry_count = retry_count + 1
                    WHERE status = 'in_progress'
                """)

                return cursor.rowcount

    def get_statistics(self):
        with self.connect() as conn:
            rows = conn.execute("""
                SELECT status, COUNT(*) AS count
                FROM jobs
                GROUP BY status
            """).fetchall()

            return {
                row["status"]: row["count"]
                for row in rows
            }
