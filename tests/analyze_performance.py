# tests/analyze_performance.py

import pandas as pd
import matplotlib.pyplot as plt
import glob
import os

def analyze_performance():
    """Analyze performance logs and generate graphs"""
    
    # Find most recent log file
    log_files = glob.glob('../server/performance_log_*.csv')
    
    if not log_files:
        print("No performance log files found!")
        return
    
    latest_log = max(log_files, key=os.path.getctime)
    print(f"Analyzing: {latest_log}")
    
    # Load data
    df = pd.read_csv(latest_log)
    
    print(f"\n{'='*60}")
    print(f"PERFORMANCE ANALYSIS")
    print(f"{'='*60}")
    print(f"Total jobs: {len(df)}")
    print(f"Job types: {df['job_type'].nunique()}")
    print(f"Workers: {df['worker_id'].nunique()}")
    
    # Summary statistics
    print(f"\n{'='*60}")
    print(f"TIMING METRICS (seconds)")
    print(f"{'='*60}")
    print(f"Queue Wait Time:")
    print(f"  Mean: {df['queue_wait'].mean():.4f}s")
    print(f"  Median: {df['queue_wait'].median():.4f}s")
    print(f"  Min: {df['queue_wait'].min():.4f}s")
    print(f"  Max: {df['queue_wait'].max():.4f}s")
    
    print(f"\nExecution Time:")
    print(f"  Mean: {df['execution_time'].mean():.4f}s")
    print(f"  Median: {df['execution_time'].median():.4f}s")
    print(f"  Min: {df['execution_time'].min():.4f}s")
    print(f"  Max: {df['execution_time'].max():.4f}s")
    
    print(f"\nTotal Response Time:")
    print(f"  Mean: {df['total_time'].mean():.4f}s")
    print(f"  Median: {df['total_time'].median():.4f}s")
    print(f"  Min: {df['total_time'].min():.4f}s")
    print(f"  Max: {df['total_time'].max():.4f}s")
    
    # Throughput calculation
    time_span = df['complete_time'].max() - df['submit_time'].min()
    throughput = len(df) / time_span
    print(f"\nThroughput: {throughput:.2f} jobs/second")
    
    # Create graphs
    create_graphs(df)
    
    print(f"\n{'='*60}")
    print(f"Graphs saved to tests/ directory")
    print(f"{'='*60}")

def create_graphs(df):
    """Generate performance visualization graphs"""
    
    # Set style
    plt.style.use('ggplot')
    
    # Graph 1: Response time distribution
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    
    # Queue wait time
    axes[0, 0].hist(df['queue_wait'], bins=30, edgecolor='black', alpha=0.7)
    axes[0, 0].set_title('Queue Wait Time Distribution')
    axes[0, 0].set_xlabel('Time (seconds)')
    axes[0, 0].set_ylabel('Frequency')
    axes[0, 0].axvline(df['queue_wait'].mean(), color='red', 
                       linestyle='--', label=f"Mean: {df['queue_wait'].mean():.3f}s")
    axes[0, 0].legend()
    
    # Execution time
    axes[0, 1].hist(df['execution_time'], bins=30, edgecolor='black', alpha=0.7, color='green')
    axes[0, 1].set_title('Execution Time Distribution')
    axes[0, 1].set_xlabel('Time (seconds)')
    axes[0, 1].set_ylabel('Frequency')
    axes[0, 1].axvline(df['execution_time'].mean(), color='red', 
                       linestyle='--', label=f"Mean: {df['execution_time'].mean():.3f}s")
    axes[0, 1].legend()
    
    # Total response time
    axes[1, 0].hist(df['total_time'], bins=30, edgecolor='black', alpha=0.7, color='orange')
    axes[1, 0].set_title('Total Response Time Distribution')
    axes[1, 0].set_xlabel('Time (seconds)')
    axes[1, 0].set_ylabel('Frequency')
    axes[1, 0].axvline(df['total_time'].mean(), color='red', 
                       linestyle='--', label=f"Mean: {df['total_time'].mean():.3f}s")
    axes[1, 0].legend()
    
    # Jobs over time
    axes[1, 1].plot(df['complete_time'] - df['complete_time'].min(), 
                    range(len(df)), marker='o', linestyle='-', markersize=2)
    axes[1, 1].set_title('Jobs Completed Over Time')
    axes[1, 1].set_xlabel('Time (seconds)')
    axes[1, 1].set_ylabel('Cumulative Jobs Completed')
    axes[1, 1].grid(True)
    
    plt.tight_layout()
    plt.savefig('performance_overview.png', dpi=300, bbox_inches='tight')
    print("[GRAPH] Saved: performance_overview.png")
    plt.close()
    
    # Graph 2: Performance by job type
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    
    job_type_stats = df.groupby('job_type')['execution_time'].agg(['mean', 'count'])
    
    axes[0].bar(job_type_stats.index, job_type_stats['mean'], edgecolor='black')
    axes[0].set_title('Average Execution Time by Job Type')
    axes[0].set_xlabel('Job Type')
    axes[0].set_ylabel('Avg Execution Time (seconds)')
    axes[0].tick_params(axis='x', rotation=45)
    
    axes[1].bar(job_type_stats.index, job_type_stats['count'], 
                edgecolor='black', color='green')
    axes[1].set_title('Job Distribution by Type')
    axes[1].set_xlabel('Job Type')
    axes[1].set_ylabel('Number of Jobs')
    axes[1].tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    plt.savefig('performance_by_jobtype.png', dpi=300, bbox_inches='tight')
    print("[GRAPH] Saved: performance_by_jobtype.png")
    plt.close()
    
    # Graph 3: Worker load distribution
    if 'worker_id' in df.columns:
        fig, ax = plt.subplots(figsize=(10, 6))
        
        worker_stats = df.groupby('worker_id').size()
        ax.bar(worker_stats.index, worker_stats.values, edgecolor='black', color='purple')
        ax.set_title('Job Distribution Across Workers')
        ax.set_xlabel('Worker ID')
        ax.set_ylabel('Number of Jobs Executed')
        ax.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        plt.savefig('worker_distribution.png', dpi=300, bbox_inches='tight')
        print("[GRAPH] Saved: worker_distribution.png")
        plt.close()

if __name__ == "__main__":
    analyze_performance()