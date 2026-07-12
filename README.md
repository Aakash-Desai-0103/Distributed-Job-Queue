# 🚀 Secure Distributed Job Queue System

A secure, fault-tolerant distributed job processing system built using **Python**, **TCP Sockets**, **SSL/TLS**, **SQLite**, and **JSON**. The system supports persistent job storage, priority scheduling, concurrent workers, automatic failure recovery, heartbeat monitoring, performance analytics, and scalability testing.

---

## ✨ Key Features

- 🔒 SSL/TLS encrypted communication
- 📦 Newline-delimited JSON messaging protocol
- 💾 SQLite-backed persistent job storage
- ⭐ Priority-based job scheduling (1–5)
- 🧵 Multi-threaded coordination server
- 👷 Distributed worker pool
- ❤️ Heartbeat-based worker monitoring
- 🔄 Automatic job re-scheduling on worker failure
- 🔁 Server restart recovery
- 📊 Performance logging & analytics
- 📈 Concurrency and scalability testing
- 🛡️ Robust malformed request handling

---

## 🏗️ System Architecture

```text
                    SUBMIT_JOB (JSON)
                           │
                           ▼
                    ┌──────────────────┐
                    │      Client      │
                    └────────┬─────────┘
                             │
                             ▼
        ┌──────────────────────────────────────┐
        │     Coordination Server (SSL/TLS)    │
        │      Multi-threaded Scheduler        │
        └────────────────┬─────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ SQLite Job Database  │
              │                      │
              │ Pending              │
              │ In Progress          │
              │ Completed            │
              └──────────┬───────────┘
                         │
                  REQUEST_JOB
                         │
                         ▼
              ┌──────────────────────┐
              │     Worker Pool      │
              │                      │
              │ Worker 1             │
              │ Worker 2             │
              │ Worker N             │
              └──────────┬───────────┘
                         │
                    COMPLETE (JSON)
                         │
                         ▼
                    SQLite Update
                         │
                         ▼
                    GETRESULT
                         │
                         ▼
                       Client
```

---

## 🧠 Distributed Systems Concepts

This project demonstrates:

- Client-Server Architecture
- Pull-Based Scheduling
- Distributed Worker Pool
- Persistent Job Queue
- Priority Scheduling
- Thread-Safe Scheduling
- Heartbeat Monitoring
- Failure Detection
- Automatic Job Recovery
- Concurrent Processing
- Secure Communication
- Performance Monitoring
- Scalability Testing
- Defensive Programming

---

## 💾 Persistent Job Storage

Unlike an in-memory queue, all jobs are stored inside a SQLite database.

Each job stores:

- Job ID
- Job Type
- Parameters (JSON)
- Priority
- Status
- Assigned Worker
- Result
- Submit Time
- Assign Time
- Completion Time
- Retry Count

The database enables:

- Server restart recovery
- Worker failure recovery
- Persistent job history
- Reliable scheduling

---

## ⭐ Priority Scheduling

The scheduler supports priorities from **1–5**.

| Priority | Description |
|----------|-------------|
| 5 | Critical |
| 4 | High |
| 3 | Normal (Default) |
| 2 | Low |
| 1 | Background |

Scheduling policy:

1. Higher priority jobs execute first.
2. Jobs with equal priority follow FIFO ordering.

---

## 🔄 Fault Tolerance Workflow

```text
Worker Failure
      │
      ▼
Heartbeat Stops
      │
      ▼
Dead Worker Detection
      │
      ▼
Identify Assigned Jobs
      │
      ▼
Re-Queue Jobs
      │
      ▼
Healthy Workers Pick Up Jobs
      │
      ▼
Successful Completion
```

The server also automatically restores unfinished jobs after a restart.

---

## 🔒 Security

All communication between clients, workers, and the server is protected using:

- SSL/TLS Encryption
- Certificate-Based Authentication
- Secure TCP Socket Communication
- Server Identity Verification

---

## ⚙️ Supported Job Types

| Job Type | Description |
|----------|-------------|
| Factorial | Compute n! |
| Fibonacci | Compute nth Fibonacci number |
| Sum | Summation workload |
| Prime | Prime number verification |
| Power | Exponentiation |
| GCD | Greatest Common Divisor |
| Sort | Sorting workload |
| Matrix | Matrix computation workload |
| Sleep | Long-running task simulation |

---

## 📡 JSON Communication Protocol

### Submit Job

```json
{
  "type": "SUBMIT_JOB",
  "job_type": "factorial",
  "priority": 5,
  "parameters": {
    "n": 10
  }
}
```

### Request Job

```json
{
  "type": "REQUEST_JOB",
  "worker_id": "worker_1"
}
```

### Complete Job

```json
{
  "type": "COMPLETE",
  "job_id": "job_15",
  "worker_id": "worker_1",
  "result": 3628800
}
```

### Get Result

```json
{
  "type": "GETRESULT",
  "job_id": "job_15"
}
```

### Heartbeat

```json
{
  "type": "HEARTBEAT",
  "worker_id": "worker_1"
}
```

---

## 📊 Performance Metrics

The server automatically records:

- Queue Wait Time
- Execution Time
- End-to-End Response Time
- Worker Utilization
- Throughput
- Job Distribution
- Completion Statistics

Performance data is exported to CSV and visualized using Matplotlib.

---

## 🧪 Testing Suite

### Client Integration Test

```bash
cd client
python3 client.py
```

Runs all supported job types through the complete system.

---

### Performance Benchmark

```bash
python3 tests/performance_test.py
```

Measures throughput under different workloads.

---

### Performance Analysis

```bash
python3 tests/analyze_performance.py
```

Generates graphs and performance statistics.

---

### Concurrent Submission Test

```bash
python3 tests/test_concurrency.py
```

Verifies thread-safe concurrent job submissions.

---

### Scalability Test

```bash
python3 tests/test_scalability.py
```

Stress-tests concurrent SSL/TLS connections.

---

### Priority Scheduling Test

```bash
python3 tests/test_priority.py
```

Verifies:

- Priority ordering
- FIFO within equal priorities
- Scheduler correctness

---

### Error Handling Test

```bash
python3 tests/test_malformed.py
```

Validates robustness against malformed requests.

---

### Fault Tolerance Demo

```bash
python3 client/demo_rescheduling.py
```

Demonstrates automatic worker failure detection and job recovery.

---

## 🚀 Getting Started

### Generate Certificates

```bash
cd server
chmod +x generate_cert.sh
./generate_cert.sh
```

---

### Start Server

```bash
cd server
python3 server.py
```

---

### Start Worker(s)

```bash
cd worker
python3 worker.py
```

Start multiple workers by opening multiple terminals.

---

### Start Client

```bash
cd client
python3 client.py
```

---

## 🛠️ Technologies Used

- Python 3
- SQLite
- TCP Sockets
- SSL/TLS
- JSON
- Threading
- OpenSSL
- Pandas
- Matplotlib

---

## 📈 Future Improvements

- 🌐 Web Monitoring Dashboard
- 🔄 Worker Auto-Reconnection
- ⚖️ Dynamic Load Balancing
- 🌍 Distributed Coordinator Replication
- 🐳 Docker Containerization
- ☸️ Kubernetes Deployment
- 🔌 REST API Gateway

---

## 🎯 Project Highlights

- Secure distributed job processing
- Persistent SQLite-backed scheduling
- Priority-aware execution
- Automatic worker failure recovery
- Server restart recovery
- Concurrent multi-worker architecture
- Thread-safe job assignment
- Performance analytics and visualization
- Scalability validated with **1000 concurrent SSL/TLS connections**
- Comprehensive automated testing

---

## 👥 Team

- **Aakash Desai**
- **Aarush Muralidhara**
- **Abhay DB**
