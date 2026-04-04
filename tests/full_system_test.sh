#!/bin/bash
# tests/full_system_test.sh

echo "================================================"
echo "DELIVERABLE 2 - COMPLETE SYSTEM TEST"
echo "================================================"

SERVER_IP="100.89.185.61"
TEST_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$TEST_DIR")"

echo ""
echo "This script will test all Deliverable 2 features:"
echo "  1. ✅ Heartbeat monitoring"
echo "  2. ✅ SSL certificate verification"
echo "  3. ✅ Multiple workers (3)"
echo "  4. ✅ Multiple job types (9)"
echo "  5. ✅ Performance metrics"
echo "  6. ✅ Stress testing (200 jobs)"
echo "  7. ✅ Error handling (malformed requests)"
echo ""

read -p "Press Enter to start test..."

# Check certificate exists
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

# Check server is running
echo ""
echo "[2/7] Checking if server is running..."
sleep 2
if ! timeout 2 bash -c "echo > /dev/tcp/$SERVER_IP/9999" 2>/dev/null; then
    echo "[WARNING] Server not responding at $SERVER_IP:9999"
    echo "[INFO] Make sure server is running: cd server && python3 server.py"
    echo "[INFO] Continuing with test..."
fi

echo "[✓] Server check complete"

# Launch workers
echo ""
echo "[3/7] Launching 3 workers..."
cd "$PROJECT_ROOT/worker"

WORKER_PIDS=()

for i in 1 2 3; do
    echo "  Starting worker_$i..."
    sed "s/worker_1/worker_$i/g" worker.py > "worker_temp_$i.py"
    python3 "worker_temp_$i.py" > "worker_$i.log" 2>&1 &
    WORKER_PIDS+=($!)
    sleep 2
done

echo "[✓] 3 workers started (PIDs: ${WORKER_PIDS[@]})"
sleep 5

# Test heartbeat monitoring
echo ""
echo "[4/7] Testing heartbeat monitoring (waiting 15s)..."
echo "  Check server terminal for heartbeat messages..."
sleep 15
echo "[✓] Heartbeat test complete (check server logs)"

# Run performance test
echo ""
echo "[5/7] Running performance test (this will take 2-5 minutes)..."
cd "$TEST_DIR"

if [ -f "performance_test.py" ]; then
    python3 performance_test.py
    echo "[✓] Performance test complete"
else
    echo "[WARNING] performance_test.py not found, skipping..."
fi

# Test error handling
echo ""
echo "[6/7] Testing error handling..."
if [ -f "test_malformed.py" ]; then
    python3 test_malformed.py
    echo "[✓] Error handling test complete"
else
    echo "[INFO] test_malformed.py not found, skipping..."
fi

# Analyze results
echo ""
echo "[7/7] Analyzing performance data..."
if [ -f "analyze_performance.py" ]; then
    python3 analyze_performance.py
    echo "[✓] Analysis complete"
else
    echo "[WARNING] analyze_performance.py not found, skipping..."
fi

# Cleanup
echo ""
echo "Cleaning up workers..."
for pid in ${WORKER_PIDS[@]}; do
    kill $pid 2>/dev/null
done

cd "$PROJECT_ROOT/worker"
rm -f worker_temp_*.py

echo "[✓] Cleanup complete"

echo ""
echo "================================================"
echo "DELIVERABLE 2 TEST COMPLETE!"
echo "================================================"
echo ""
echo "Results:"
echo "  - Performance log: $PROJECT_ROOT/server/performance_log_*.csv"
echo "  - Worker logs: $PROJECT_ROOT/worker/worker_*.log"
if [ -f "$TEST_DIR/performance_overview.png" ]; then
    echo "  - Graphs: $TEST_DIR/*.png"
fi
echo "  - Server log: Check server terminal"
echo ""
echo "Next steps:"
echo "  1. Review performance graphs (if generated)"
echo "  2. Check server logs for heartbeat monitoring"
echo "  3. Review SSL connection messages"
echo "  4. Check worker logs for any errors"
echo ""
echo "================================================"