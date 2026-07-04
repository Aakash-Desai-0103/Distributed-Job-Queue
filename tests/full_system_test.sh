#!/bin/bash
# tests/full_system_test.sh

SERVER_IP="127.0.0.1"
TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$TEST_DIR")"
WORKER_PIDS=()

cleanup() {
    echo ""
    echo "Cleaning up workers..."
    for pid in "${WORKER_PIDS[@]}"; do
        kill "$pid" 2>/dev/null
    done
    rm -f "$PROJECT_ROOT"/worker/worker_temp_*.py
    echo "[✓] Cleanup complete"
}

trap cleanup EXIT INT TERM

echo "================================================"
echo "DISTRIBUTED JOB QUEUE - COMPLETE SYSTEM TEST"
echo "================================================"
echo ""
echo "This script will test:"
echo "  1. SSL certificate verification"
echo "  2. Multiple workers"
echo "  3. Heartbeat monitoring"
echo "  4. Multiple job types"
echo "  5. Performance metrics"
echo "  6. Stress testing"
echo "  7. Error handling"
echo ""

read -p "Press Enter to start test..."

echo ""
echo "[1/7] Checking SSL certificates..."

if [ ! -f "$PROJECT_ROOT/server/cert.pem" ]; then
    echo "[ERROR] Server certificate not found!"
    echo "[INFO] Run: cd server && ./generate_cert.sh"
    exit 1
fi

if [ ! -f "$PROJECT_ROOT/worker/cert.pem" ]; then
    echo "[INFO] Copying certificate to worker..."
    cp "$PROJECT_ROOT/server/cert.pem" "$PROJECT_ROOT/worker/"
fi

if [ ! -f "$PROJECT_ROOT/client/cert.pem" ]; then
    echo "[INFO] Copying certificate to client..."
    cp "$PROJECT_ROOT/server/cert.pem" "$PROJECT_ROOT/client/"
fi

echo "[✓] Certificates ready"

echo ""
echo "[2/7] Checking if server is running..."
sleep 2

if ! timeout 2 bash -c "echo > /dev/tcp/$SERVER_IP/9999" 2>/dev/null; then
    echo "[ERROR] Server not responding at $SERVER_IP:9999"
    echo "[INFO] Start it with: cd server && python3 server.py"
    exit 1
fi

echo "[✓] Server port is reachable"

echo ""
echo "[3/7] Launching 3 workers..."
cd "$PROJECT_ROOT/worker" || exit 1

for i in 1 2 3; do
    echo "  Starting worker_$i..."
    sed "s/'worker_1'/'worker_$i'/g" worker.py > "worker_temp_$i.py"
    python3 "worker_temp_$i.py" > "worker_$i.log" 2>&1 &
    WORKER_PIDS+=("$!")
    sleep 2
done

echo "[✓] 3 workers started (PIDs: ${WORKER_PIDS[*]})"
sleep 5

echo ""
echo "[4/7] Testing heartbeat monitoring (waiting 15s)..."
echo "  Check server terminal for heartbeat messages..."
sleep 15
echo "[✓] Heartbeat observation period complete"

echo ""
echo "[5/7] Running performance test..."
cd "$TEST_DIR" || exit 1

if python3 performance_test.py; then
    echo "[✓] Performance test complete"
else
    echo "[✗] Performance test failed"
    exit 1
fi

echo ""
echo "[6/7] Testing error handling..."

if python3 test_malformed.py; then
    echo "[✓] Error handling test complete"
else
    echo "[✗] Error handling test failed"
    exit 1
fi

echo ""
echo "[7/7] Analyzing performance data..."

if python3 analyze_performance.py; then
    echo "[✓] Analysis complete"
else
    echo "[✗] Performance analysis failed"
    exit 1
fi

echo ""
echo "================================================"
echo "COMPLETE SYSTEM TEST FINISHED"
echo "================================================"
echo ""
echo "Results:"
echo "  - Performance logs: $PROJECT_ROOT/server/performance_log_*.csv"
echo "  - Worker logs: $PROJECT_ROOT/worker/worker_*.log"

if [ -f "$TEST_DIR/performance_overview.png" ]; then
    echo "  - Graphs: $TEST_DIR/*.png"
fi

echo "  - Server activity: Check server terminal"
echo ""
echo "================================================"
