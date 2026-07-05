#!/usr/bin/env python3

import sys
import threading

sys.path.append("..")

from client.client import JobSubmitter


SERVER_IP = "127.0.0.1"

NUM_CLIENTS = 5
JOBS_PER_CLIENT = 10

submitted_ids = []
failed_submissions = 0
lock = threading.Lock()


def submit_jobs(client_number):
    global failed_submissions

    client = JobSubmitter(SERVER_IP)

    try:
        client.connect()

        local_ids = []

        for i in range(JOBS_PER_CLIENT):
            job_id = client.submit_job(
                "sleep",
                duration=2
            )

            if job_id:
                local_ids.append(job_id)
            else:
                with lock:
                    failed_submissions += 1

        with lock:
            submitted_ids.extend(local_ids)

    except Exception as e:
        print(f"[CLIENT {client_number}] Error: {e}")

        with lock:
            failed_submissions += JOBS_PER_CLIENT

    finally:
        client.close()


if __name__ == "__main__":
    print("=" * 60)
    print("CONCURRENT SUBMISSION TEST")
    print("=" * 60)

    threads = []

    for i in range(NUM_CLIENTS):
        thread = threading.Thread(
            target=submit_jobs,
            args=(i + 1,)
        )

        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    total = len(submitted_ids)
    unique = len(set(submitted_ids))

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    print(f"Expected submissions: {NUM_CLIENTS * JOBS_PER_CLIENT}")
    print(f"Successful submissions: {total}")
    print(f"Unique job IDs: {unique}")
    print(f"Failed submissions: {failed_submissions}")

    duplicates = total - unique

    print(f"Duplicate IDs: {duplicates}")

    if (
        total == NUM_CLIENTS * JOBS_PER_CLIENT
        and unique == total
        and failed_submissions == 0
    ):
        print("\n✅ CONCURRENT SUBMISSION TEST PASSED")
    else:
        print("\n❌ CONCURRENT SUBMISSION TEST FAILED")
