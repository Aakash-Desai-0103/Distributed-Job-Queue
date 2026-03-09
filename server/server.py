import socket

HOST = "0.0.0.0"
PORT = 9999

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen()

print(f"Server listening on port {PORT}")

while True:
    conn, addr = server.accept()
    print("Connected from:", addr)

    message = "Hello from Distributed Job Queue Server!\n"
    conn.send(message.encode())

    conn.close()