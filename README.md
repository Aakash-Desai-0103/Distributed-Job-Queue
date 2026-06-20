# 🚀 Secure Distributed Job Queue System

A fault-tolerant distributed job processing system built using **Python**, **TCP Sockets**, and **SSL/TLS**. The system supports secure communication, concurrent workers, heartbeat monitoring, automatic job re-scheduling, performance analytics, and scalability testing.

---

## ✨ Key Features

* 🔒 SSL/TLS encrypted communication
* 🧵 Multi-threaded coordination server
* ⚡ Asynchronous job execution
* 👷 Multiple worker nodes
* ❤️ Heartbeat-based worker monitoring
* 🔄 Automatic job re-scheduling on worker failure
* 📊 Performance logging & analytics
* 📈 Throughput and scalability testing
* 🛡️ Robust malformed request handling
* 🔍 Detailed observability and metrics collection

---

## 🏗️ System Architecture

```text
                    SUBMIT_JOB
Client --------------------------------→ Server
                                           │
                                           │
                                           ▼
                                    Pending Queue
                                           │
                                           │
                                    REQUEST_JOB
                                           │
                                           ▼
                                      Worker Pool
                                  ┌─────────────┐
                                  │ Worker 1    │
                                  │ Worker 2    │
                                  │ Worker N    │
                                  └─────────────┘
                                           │
                                           ▼
                                      COMPLETE
                                           │
                                           ▼
                                        Server
                                           │
                                           ▼
                                     GETRESULT
                                           │
                                           ▼
                                        Client
```

### Design Highlights

✅ Pull-Based Scheduling

✅ Thread-Safe Job Management

✅ Distributed Worker Pool

✅ Fault Tolerant Execution

✅ Secure Communication Layer

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
Reconstruct Job Details
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

---

## 🧠 Distributed Systems Concepts

This project demonstrates:

* Client-Server Architecture
* Worker Pool Design
* Pull-Based Scheduling
* Heartbeat Monitoring
* Failure Detection
* Fault Tolerance
* Job Re-Scheduling
* Secure Communication
* Concurrent Processing
* Performance Observability
* Scalability Testing
* Defensive Programming

---

## 🔒 Security

All communication between clients, workers, and the server is protected using:

* SSL/TLS Encryption
* Certificate-Based Verification
* Secure Socket Communication
* Server Identity Validation

---

## ⚙️ Supported Job Types

| Job Type  | Description                  |
| --------- | ---------------------------- |
| Factorial | Compute n!                   |
| Fibonacci | Compute nth Fibonacci number |
| Sum       | Summation workload           |
| Prime     | Prime number verification    |
| Power     | Exponentiation               |
| GCD       | Greatest Common Divisor      |
| Sort      | Sorting workload             |
| Matrix    | Matrix computation workload  |
| Sleep     | Long-running task simulation |

---

## 📡 Communication Protocol

### Submit Job

```text
SUBMIT_JOB|factorial|n=10
```

### Request Work

```text
REQUEST_JOB|worker_1
```

### Complete Job

```text
COMPLETE|job_1|3628800
```

### Retrieve Result

```text
GETRESULT|job_1
```

### Heartbeat

```text
HEARTBEAT|worker_1
```

---

## 📊 Performance Metrics

The system automatically records:

* Queue Wait Time
* Execution Time
* End-to-End Latency
* Worker Utilization
* Throughput
* Job Distribution Statistics

Performance data is exported to CSV and visualized using Matplotlib.

---

## 🧪 Testing Suite

### Performance Benchmarking

```bash
python3 tests/performance_test.py
```

Measures throughput and workload handling.

---

### Performance Analysis

```bash
python3 tests/analyze_performance.py
```

Generates statistics and visualizations.

---

### Scalability Testing

```bash
python3 tests/test_scalability.py
```

Evaluates concurrent connection capacity.

---

### Error Handling Validation

```bash
python3 tests/test_malformed.py
```

Tests robustness against malformed requests.

---

### Fault Tolerance Demonstration

```bash
python3 client/demo_rescheduling.py
```

Demonstrates automatic job recovery and re-scheduling.

---

## 🚀 Getting Started

### Generate Certificates

```bash
cd server
chmod +x generate_cert.sh
./generate_cert.sh
```

### Start Server

```bash
cd server
python3 server.py
```

### Start Worker(s)

```bash
cd worker
python3 worker.py
```

### Start Client

```bash
cd client
python3 client.py
```

---

## 📈 Future Improvements

* Persistent Job Storage (SQLite/PostgreSQL)
* Priority-Based Scheduling
* Web Monitoring Dashboard
* Worker Auto-Reconnection
* Distributed Server Replication
* Advanced Load Balancing

---

## 🎯 Project Highlights

* Secure Distributed Job Processing
* Automatic Worker Failure Recovery
* Real-Time Performance Monitoring
* Scalable Multi-Worker Architecture
* Comprehensive Testing Infrastructure
* End-to-End SSL/TLS Security
