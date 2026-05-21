import socket
import threading
import json
import os

# Render קובע את הפורט אוטומטית, ואם לא - נשתמש ב-10000 כגיבוי
PORT = int(os.environ.get("PORT", 10000))
HOST = '0.0.0.0' # מקשיב לכל העולם

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    server.bind((HOST, PORT))
except socket.error as e:
    print(str(e))

server.listen()
print(f"[SERVER STARTED] Listening on global port {PORT}...")

active_lobbies = {}

def handle_client(conn, addr):
    print(f"[NEW CONNECTION] {addr} connected.")
    current_lobby_id = None

    while True:
        try:
            data = conn.recv(2048).decode('utf-8')
            if not data:
                break

            request = json.loads(data)
            action = request.get("action")

            if action == "create_lobby":
                current_lobby_id = str(addr[1])
                active_lobbies[current_lobby_id] = {
                    "name": f"Room_{current_lobby_id}",
                    "ping": "30ms",
                    "players": "1/4",
                    "status": "In Lobby"
                }
                conn.send(json.dumps({"status": "success", "lobby_id": current_lobby_id}).encode('utf-8'))
                print(f"[LOBBY CREATED] {active_lobbies[current_lobby_id]['name']}")

            elif action == "get_servers":
                server_list = list(active_lobbies.values())
                conn.send(json.dumps(server_list).encode('utf-8'))

        except:
            break

    if current_lobby_id in active_lobbies:
        print(f"[LOBBY CLOSED] {active_lobbies[current_lobby_id]['name']}")
        del active_lobbies[current_lobby_id]

    conn.close()

while True:
    conn, addr = server.accept()
    thread = threading.Thread(target=handle_client, args=(conn, addr))
    thread.start()