# tests/performance_test.py

import sys
sys.path.append('..')

from client.client import JobSubmitter
import time
import random

class PerformanceTester:
    def __init__(self, server_ip):
        self.server_ip = server_ip
        self.client = None
    
    def connect(self):
        """Connect to server"""
        self.client = JobSubmitter(self.server_ip)
        self.client.connect()
        print("[TEST] Connected to server")
    
    def run_test(self, num_jobs=100, job_mix='mixed'):
        """Run performance test with specified number of jobs"""
        print(f"\n{'='*60}")
        print(f"PERFORMANCE TEST: {num_jobs} jobs ({job_mix} mix)")
        print(f"{'='*60}\n")
        
        jobs = []
        start_time = time.time()
        
        # Submit jobs
        print(f"[SUBMIT] Submitting {num_jobs} jobs...")
        for i in range(num_jobs):
            job_type, params = self.generate_job(i, job_mix)
            job_id = self.client.submit_job(job_type, **params)
            if job_id:
                jobs.append(job_id)
            
            # Small delay to avoid overwhelming server
            if i % 10 == 0:
                time.sleep(0.1)
        
        submission_time = time.time() - start_time
        print(f"[SUBMIT] All jobs submitted in {submission_time:.2f}s")
        
        # Wait for completion
        print(f"\n[WAIT] Waiting for all jobs to complete...")
        completed = 0
        start_wait = time.time()
        
        for job_id in jobs:
            result = self.client.get_result(job_id, max_wait=120, poll_interval=1)
            if result is not None:
                completed += 1
                if completed % 10 == 0:
                    print(f"[PROGRESS] {completed}/{num_jobs} jobs completed")
        
        total_time = time.time() - start_time
        
        # Results
        print(f"\n{'='*60}")
        print(f"RESULTS:")
        print(f"  Total jobs: {num_jobs}")
        print(f"  Completed: {completed}")
        print(f"  Failed: {num_jobs - completed}")
        print(f"  Submission time: {submission_time:.2f}s")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Throughput: {completed/total_time:.2f} jobs/second")
        print(f"{'='*60}\n")
    
    def generate_job(self, index, mix_type='mixed'):
        """Generate a job based on mix type"""
        
        if mix_type == 'factorial':
            return ('factorial', {'n': random.randint(5, 15)})
        
        elif mix_type == 'fibonacci':
            return ('fibonacci', {'n': random.randint(10, 30)})
        
        elif mix_type == 'compute':
            # CPU-intensive jobs
            job_types = [
                ('factorial', {'n': random.randint(10, 20)}),
                ('fibonacci', {'n': random.randint(20, 35)}),
                ('prime', {'n': random.randint(1000, 10000)}),
                ('power', {'x': random.randint(2, 10), 'y': random.randint(10, 15)}),
                ('gcd', {'a': random.randint(100, 1000), 'b': random.randint(100, 1000)}),
            ]
            job_type, params = random.choice(job_types)
            return (job_type, params)
        
        elif mix_type == 'mixed':
            # Mix of all job types
            job_types = [
                ('factorial', {'n': random.randint(5, 15)}),
                ('fibonacci', {'n': random.randint(10, 30)}),
                ('sum', {'limit': random.randint(100, 1000)}),
                ('prime', {'n': random.randint(1000, 10000)}),
                ('power', {'x': random.randint(2, 10), 'y': random.randint(5, 12)}),
                ('gcd', {'a': random.randint(50, 500), 'b': random.randint(50, 500)}),
                ('sort', {'size': random.randint(100, 1000)}),
                ('matrix', {'size': random.randint(5, 15)}),
            ]
            job_type, params = random.choice(job_types)
            return (job_type, params)
        
        else:
            return ('factorial', {'n': 10})
    
    def close(self):
        """Close connection"""
        if self.client:
            self.client.close()

if __name__ == "__main__":
    SERVER_IP = '100.89.185.61'
    
    tester = PerformanceTester(SERVER_IP)
    tester.connect()
    
    # Run different test scenarios
    print("\n" + "="*60)
    print("STARTING PERFORMANCE TESTS")
    print("="*60)
    
    # Test 1: 50 jobs, mixed workload
    tester.run_test(num_jobs=50, job_mix='mixed')
    time.sleep(2)
    
    # Test 2: 100 jobs, compute-heavy
    tester.run_test(num_jobs=100, job_mix='compute')
    time.sleep(2)
    
    # Test 3: 200 jobs, mixed workload (stress test)
    tester.run_test(num_jobs=200, job_mix='mixed')
    
    tester.close()
    
    print("\n" + "="*60)
    print("ALL TESTS COMPLETE")
    print("Check server directory for performance_log_*.csv")
    print("="*60)