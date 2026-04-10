#!/usr/bin/env python3
# tests/test_scalability.py - Test maximum concurrent connections

import socket
import ssl
import threading
import time

SERVER_IP = '10.20.204.2'
SERVER_PORT = 9999
CERT_PATH = '../client/cert.pem'

MAX_CONNECTIONS = 1024  # System-safe limit

successful_connections = 0
failed_connections = 0
active_sockets = []  # To keep connections alive
lock = threading.Lock()


def test_connection(worker_id):
    global successful_connections, failed_connections

    try:
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.load_verify_locations(CERT_PATH)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_REQUIRED

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)  # Prevent hanging connections

        ssl_sock = context.wrap_socket(sock, server_hostname=SERVER_IP)
        ssl_sock.connect((SERVER_IP, SERVER_PORT))

        # Send heartbeat
        ssl_sock.send(f"HEARTBEAT|scalability_test_{worker_id}\n".encode())
        response = ssl_sock.recv(1024).decode()

        if response.startswith("OK"):
            with lock:
                successful_connections += 1
                active_sockets.append(ssl_sock)  # Keep connection alive
        else:
            with lock:
                failed_connections += 1
            ssl_sock.close()

    except Exception as e:
        with lock:
            failed_connections += 1
        print(f"[!] Connection {worker_id} failed: {e}")


if __name__ == "__main__":
    print("SCALABILITY TEST")
    print("=" * 60)

    # Input with validation
    try:
        num_connections = int(input("How many concurrent connections to test? "))
    except ValueError:
        print("Invalid input. Please enter a number.")
        exit(1)

    # Enforce limit
    if num_connections <= 0:
        print("Number must be greater than 0.")
        exit(1)

    if num_connections >= MAX_CONNECTIONS:
        print(f"[!] Limiting connections to {MAX_CONNECTIONS - 1} (system-safe limit)")
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

        # Prevent sudden burst overload
        if i % 50 == 0:
            time.sleep(0.05)

    # Wait for all threads
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
    print(f"Connection rate: {successful_connections / elapsed:.2f} connections/sec")
    print("=" * 60)

    # Keep connections alive
    print("\nKeeping connections alive for 30 seconds...")
    time.sleep(30)

    # Cleanup
    print("\nClosing all connections...")
    for sock in active_sockets:
        try:
            sock.close()
        except:
            pass

    print("Test complete!")
