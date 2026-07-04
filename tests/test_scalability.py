#!/usr/bin/env python3
# tests/test_scalability.py - Test maximum concurrent connections

import socket
import ssl
import threading
import time
import json
import sys

SERVER_IP = '127.0.0.1'
SERVER_PORT = 9999
CERT_PATH = '../client/cert.pem'
MAX_CONNECTIONS = 1024

successful_connections = 0
failed_connections = 0
active_sockets = []
lock = threading.Lock()


def test_connection(worker_id):
    global successful_connections, failed_connections

    ssl_sock = None

    try:
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.load_verify_locations(CERT_PATH)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_REQUIRED

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)

        ssl_sock = context.wrap_socket(sock, server_hostname=SERVER_IP)
        ssl_sock.connect((SERVER_IP, SERVER_PORT))

        message = {
            "type": "HEARTBEAT",
            "worker_id": f"scalability_test_{worker_id}"
        }

        ssl_sock.sendall(
            (json.dumps(message) + "\n").encode("utf-8")
        )

        buffer = ""

        while "\n" not in buffer:
            chunk = ssl_sock.recv(4096).decode("utf-8")

            if not chunk:
                raise ConnectionError("Server closed connection")

            buffer += chunk

        line, _ = buffer.split("\n", 1)
        response = json.loads(line)

        if response.get("type") == "OK":
            with lock:
                successful_connections += 1
                active_sockets.append(ssl_sock)
        else:
            with lock:
                failed_connections += 1

            ssl_sock.close()

    except Exception as e:
        with lock:
            failed_connections += 1

        if ssl_sock:
            try:
                ssl_sock.close()
            except Exception:
                pass

        print(f"[!] Connection {worker_id} failed: {e}")


if __name__ == "__main__":
    print("SCALABILITY TEST")
    print("=" * 60)

    try:
        num_connections = int(
            input("How many concurrent connections to test? ")
        )
    except ValueError:
        print("Invalid input. Please enter a number.")
        sys.exit(1)

    if num_connections <= 0:
        print("Number must be greater than 0.")
        sys.exit(1)

    if num_connections >= MAX_CONNECTIONS:
        print(
            f"[!] Limiting connections to "
            f"{MAX_CONNECTIONS - 1}"
        )
        num_connections = MAX_CONNECTIONS - 1

    threads = []
    start_time = time.time()

    print(f"\nCreating {num_connections} concurrent connections...")

    for i in range(num_connections):
        thread = threading.Thread(
            target=test_connection,
            args=(i,),
            daemon=True
        )

        threads.append(thread)
        thread.start()

        if i > 0 and i % 50 == 0:
            time.sleep(0.05)

    for thread in threads:
        thread.join()

    elapsed = time.time() - start_time

    print("\n" + "=" * 60)
    print("SCALABILITY TEST RESULTS")
    print("=" * 60)
    print(f"Total attempted: {num_connections}")
    print(f"Successful: {successful_connections}")
    print(f"Failed: {failed_connections}")
    print(f"Time elapsed: {elapsed:.2f}s")

    if elapsed > 0:
        rate = successful_connections / elapsed
        print(f"Connection rate: {rate:.2f} connections/sec")

    print("=" * 60)

    print("\nKeeping connections alive for 30 seconds...")
    time.sleep(30)

    print("\nClosing all connections...")

    for sock in active_sockets:
        try:
            sock.close()
        except Exception:
            pass

    print("Test complete!")
