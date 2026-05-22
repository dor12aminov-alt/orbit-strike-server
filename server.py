import socket
import threading
import json
import os

# הגדרות שרת
PORT = int(os.environ.get("PORT", 10000))
HOST = '0.0.0.0'

# מבנה הנתונים שלנו:
# lobbies = { "room_id": { "players": { "addr1": {"x": 0, "y": 0, "hp": 100}, "addr2": {...} } } }
lobbies = {}
data_lock = threading.Lock()

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # מאפשר הפעלה מחדש מהירה
try:
    server.bind((HOST, PORT))
except socket.error as e:
    print(f"[ERROR] {e}")

server.listen()
print(f"[SERVER STARTED] Listening on port {PORT}...")

def handle_client(conn, addr):
    addr_str = str(addr)
    current_lobby = None
    print(f"[NEW CONNECTION] {addr} connected.")

    while True:
        try:
            data = conn.recv(2048).decode('utf-8')
            if not data: break

            request = json.loads(data)
            action = request.get("action")

            # 1. יצירת לובי
            if action == "create_lobby":
                lobby_id = str(addr[1]) # משתמש בפורט של השחקן בתור מזהה ייחודי
                with data_lock:
                    lobbies[lobby_id] = {"players": {}}
                    current_lobby = lobby_id
                conn.send(json.dumps({"status": "success", "lobby_id": lobby_id}).encode())
                print(f"[LOBBY CREATED] ID: {lobby_id}")

            # 2. הצטרפות ללובי
            elif action == "join_lobby":
                target_id = request.get("lobby_id")
                with data_lock:
                    if target_id in lobbies:
                        current_lobby = target_id
                        conn.send(json.dumps({"status": "success"}).encode())
                    else:
                        conn.send(json.dumps({"status": "error", "msg": "Lobby not found"}).encode())

            # 3. קבלת רשימת לוביז
            elif action == "get_lobbies":
                with data_lock:
                    rooms = list(lobbies.keys())
                    conn.send(json.dumps(rooms).encode())

            # 4. סנכרון נתונים (הלב של המשחק)
            elif action == "update":
                lobby_id = request.get("lobby_id")
                player_data = request.get("data")
                
                with data_lock:
                    if lobby_id in lobbies:
                        # עדכון הנתונים של השחקן הנוכחי
                        lobbies[lobby_id]["players"][addr_str] = player_data
                        
                        # שליפת כל השחקנים האחרים בחדר
                        other_players = [
                            {"addr": a, "data": d} 
                            for a, d in lobbies[lobby_id]["players"].items() 
                            if a != addr_str
                        ]
                        conn.send(json.dumps({"players": other_players}).encode())

        except Exception as e:
            print(f"[ERROR] {e}")
            break

    # ניקוי בזמן התנתקות
    if current_lobby:
        with data_lock:
            if current_lobby in lobbies and addr_str in lobbies[current_lobby]["players"]:
                del lobbies[current_lobby]["players"][addr_str]
                # אם הלובי ריק, אפשר למחוק אותו
                if not lobbies[current_lobby]["players"]:
                    del lobbies[current_lobby]
                    print(f"[LOBBY REMOVED] {current_lobby}")

    conn.close()
    print(f"[DISCONNECTED] {addr}")

while True:
    conn, addr = server.accept()
    thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
    thread.start()
