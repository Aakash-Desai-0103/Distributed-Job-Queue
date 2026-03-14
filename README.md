# Secure Distributed Job Queue System

## Team Members
- Member 1: Job Submitter Client (macOS)
- Member 2: Central Coordination Server (Linux)
- Member 3: Worker Node (Windows VM)

## Overview
Distributed job queue system with SSL/TLS encryption for secure communication.

## Architecture
- **Centralized client-server** with distributed workers
- **Pull-based scheduling** - workers request jobs when ready
- **SSL/TLS encryption** - all communication secured
- **Multi-threaded server** - handles concurrent clients

## Features
✅ TCP socket programming (Port 9999)
✅ SSL/TLS encryption
✅ Thread-safe job queue
✅ Multiple concurrent clients
✅ 4 job types: factorial, fibonacci, sum, sleep

## Prerequisites
- Python 3.x
- OpenSSL (for certificates)
- Tailscale VPN (for distributed setup)

## Setup

### 1. Generate SSL Certificates (Server Only)
```bash
cd server
openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes
```

### 2. Run Components

**Server:**
```bash
cd server
python3 server.py
```

**Worker:**
```bash
cd worker
python3 worker.py
```

**Client:**
```bash
cd client
python3 client.py
```

## Results
All tests passed successfully:
- factorial(10) = 3,628,800 ✓
- factorial(5) = 120 ✓
- fibonacci(10) = 55 ✓
- sum(1..100) = 5,050 ✓

## Protocol
- **Transport:** TCP sockets (Port 9999)
- **Security:** SSL/TLS encryption
- **Format:** JSON messages with \n delimiter
- **Message Types:** SUBMIT_JOB, REQUEST_JOB, JOB_COMPLETE, GET_RESULT

## Status
✅ Deliverable 1 Complete
⏳ Deliverable 2 In Progress (Heartbeat, Performance)
