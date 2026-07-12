import sys
import time

sys.path.append("..")

from client.client import JobSubmitter


SERVER_IP = "127.0.0.1"


def main():
    client = JobSubmitter(SERVER_IP, cert_path="cert.pem")
    client.connect()

    print("\n" + "=" * 60)
    print("PRIORITY SCHEDULING TEST")
    print("=" * 60)

    jobs = []

    test_jobs = [
        ("factorial", 1, {"n": 10}),
        ("sleep", 5, {"duration": 2}),
        ("fibonacci", 3, {"n": 15}),
        ("gcd", 2, {"a": 48, "b": 18}),
        ("power", 5, {"x": 2, "y": 10}),
        ("matrix", 4, {"size": 10}),
    ]

    print("\nSubmitting jobs...\n")

    for job_type, priority, params in test_jobs:
        job_id = client.submit_job(
            job_type,
            priority=priority,
            **params
        )

        jobs.append((job_id, job_type, priority))

    print("\nSubmitted Jobs")
    print("-" * 60)

    for job_id, job_type, priority in jobs:
        print(
            f"{job_id:<8}"
            f"{job_type:<12}"
            f"Priority {priority}"
        )

    print("\nStart one or more workers if they are not already running.")
    input("Press Enter once workers are running...")

    print("\nWaiting for completion...\n")

    for job_id, job_type, priority in jobs:
        client.get_result(
            job_id,
            max_wait=60,
            poll_interval=1
        )

    print("\n" + "=" * 60)
    print("PRIORITY TEST COMPLETE")
    print("=" * 60)

    print("\nExpected execution order:")

    expected = sorted(
        jobs,
        key=lambda x: (-x[2], x[0])
    )

    for _, job_type, priority in expected:
        print(
            f"Priority {priority} -> {job_type}"
        )

    client.close()


if __name__ == "__main__":
    main()
