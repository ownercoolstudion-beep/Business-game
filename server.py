"""
BUSINESS EMPIRE SERVER
Startet mit: python server.py
Braucht KEINE externen Pakete - nur Python (bereits auf Windows installiert)
"""
import http.server
import json
import os
import hashlib
import time
import random
import string
from urllib.parse import urlparse, parse_qs

PORT = 3000
DB_FILE = "database.json"

# ─── Database ───────────────────────────────────────────────
def load_db():
    if not os.path.exists(DB_FILE):
        db = {"users": {}, "leaderboard": [], "sessions": {}}
        save_db(db)
        return db
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def gen_token():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=32))

def get_local_ip():
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "localhost"

# ─── Request Handler ────────────────────────────────────────
class GameHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        # Only log API calls
        if "/api/" in self.path:
            print(f"  [{time.strftime('%H:%M:%S')}] {self.path} - {args[1]}")

    def send_json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, msg, code=400):
        self.send_json({"error": msg}, code)

    def get_token(self):
        auth = self.headers.get("Authorization", "")
        return auth.replace("Bearer ", "").strip() if auth else None

    def get_user_from_token(self, db):
        token = self.get_token()
        if not token:
            return None, None
        username = db["sessions"].get(token)
        if not username or username not in db["users"]:
            return None, None
        return username, db["users"][username]

    def read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        try:
            return json.loads(self.body_raw[:length])
        except:
            return {}

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/api/status":
            db = load_db()
            self.send_json({
                "status": "online",
                "game": "Business Empire v0.0.6",
                "players": len(db["users"]),
                "uptime": int(time.time() - START_TIME)
            })
            return

        if path == "/api/profile":
            db = load_db()
            uname, user = self.get_user_from_token(db)
            if not uname:
                self.send_error_json("Nicht eingeloggt.", 401)
                return
            safe = {k: v for k, v in user.items() if k != "password"}
            safe["username"] = uname
            self.send_json(safe)
            return

        if path == "/api/leaderboard":
            db = load_db()
            self.send_json({"leaderboard": db.get("leaderboard", [])})
            return

        if path == "/api/saves":
            db = load_db()
            uname, user = self.get_user_from_token(db)
            if not uname:
                self.send_error_json("Nicht eingeloggt.", 401)
                return
            saves = user.get("saves", {})
            # Return only metadata (no heavy cell data)
            meta = {}
            for slot, s in saves.items():
                if s:
                    meta[slot] = {
                        "day": s.get("day"), "money": s.get("money"),
                        "level": s.get("level"), "currentSize": s.get("currentSize"),
                        "savedAt": s.get("savedAt")
                    }
            self.send_json({"saves": meta})
            return

        if path.startswith("/api/save/"):
            slot = path.replace("/api/save/", "")
            db = load_db()
            uname, user = self.get_user_from_token(db)
            if not uname:
                self.send_error_json("Nicht eingeloggt.", 401)
                return
            saves = user.get("saves", {})
            self.send_json({"save": saves.get(slot)})
            return

        if path == "/api/online":
            db = load_db()
            self.send_json({"count": len(db["sessions"])})
            return

        # Serve files
        if path == "/" or path == "":
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        self.body_raw = self.rfile.read(length) if length > 0 else b"{}"
        body = {}
        try:
            body = json.loads(self.body_raw)
        except:
            pass

        path = urlparse(self.path).path

        # ── REGISTER ──────────────────────────────────────
        if path == "/api/register":
            username = body.get("username", "").strip()
            password = body.get("password", "")
            avatar   = body.get("avatar", "🏢")

            if not username or not password:
                self.send_error_json("Benutzername und Passwort erforderlich.")
                return
            if len(username) < 3 or len(username) > 20:
                self.send_error_json("Benutzername: 3-20 Zeichen.")
                return
            if len(password) < 4:
                self.send_error_json("Passwort: mindestens 4 Zeichen.")
                return

            db = load_db()
            if username in db["users"]:
                self.send_error_json("Benutzername bereits vergeben.")
                return

            token = gen_token()
            db["users"][username] = {
                "password": hash_pw(password),
                "avatar": avatar,
                "created": int(time.time()),
                "wins": 0, "games": 0, "earned": 0,
                "buildings": 0, "upgrades": 0, "days": 0,
                "achDone": [], "lastDaily": 0, "saves": {}
            }
            db["sessions"][token] = username
            save_db(db)
            print(f"  ✅ Neuer Spieler: {username}")

            user_safe = {k: v for k, v in db["users"][username].items() if k != "password"}
            self.send_json({"success": True, "token": token, "username": username, "user": user_safe})
            return

        # ── LOGIN ──────────────────────────────────────────
        if path == "/api/login":
            username = body.get("username", "").strip()
            password = body.get("password", "")
            db = load_db()

            if username not in db["users"]:
                self.send_error_json("Benutzer nicht gefunden.")
                return
            if db["users"][username]["password"] != hash_pw(password):
                self.send_error_json("Falsches Passwort.")
                return

            token = gen_token()
            db["sessions"][token] = username
            save_db(db)
            print(f"  🔑 Login: {username}")

            user_safe = {k: v for k, v in db["users"][username].items() if k != "password"}
            self.send_json({"success": True, "token": token, "username": username, "user": user_safe})
            return

        # ── LOGOUT ────────────────────────────────────────
        if path == "/api/logout":
            token = self.get_token()
            if token:
                db = load_db()
                db["sessions"].pop(token, None)
                save_db(db)
            self.send_json({"success": True})
            return

        # ── UPDATE PROFILE ────────────────────────────────
        if path == "/api/profile/update":
            db = load_db()
            uname, user = self.get_user_from_token(db)
            if not uname:
                self.send_error_json("Nicht eingeloggt.", 401)
                return
            allowed = ["wins","games","earned","buildings","upgrades","days","achDone","lastDaily"]
            for k in allowed:
                if k in body:
                    db["users"][uname][k] = body[k]
            save_db(db)
            self.send_json({"success": True})
            return

        # ── SAVE GAME ─────────────────────────────────────
        if path.startswith("/api/save/"):
            slot = path.replace("/api/save/", "")
            if slot not in ["0","1","2","auto"]:
                self.send_error_json("Ungültiger Slot.")
                return
            db = load_db()
            uname, user = self.get_user_from_token(db)
            if not uname:
                self.send_error_json("Nicht eingeloggt.", 401)
                return
            if "saves" not in db["users"][uname]:
                db["users"][uname]["saves"] = {}
            body["savedAt"] = int(time.time() * 1000)
            db["users"][uname]["saves"][slot] = body
            save_db(db)
            print(f"  💾 Spielstand: {uname} Slot {slot}")
            self.send_json({"success": True})
            return

        # ── LEADERBOARD ───────────────────────────────────
        if path == "/api/leaderboard":
            db = load_db()
            uname, _ = self.get_user_from_token(db)
            name  = uname or body.get("name", "Anonym")
            money = body.get("money", 0)
            day   = body.get("day", 0)

            if not money or not day:
                self.send_error_json("Fehlende Daten.")
                return

            if "leaderboard" not in db:
                db["leaderboard"] = []
            db["leaderboard"].append({
                "name": name, "money": money, "day": day,
                "map": body.get("map"), "diff": body.get("diff"),
                "ts": int(time.time() * 1000)
            })
            db["leaderboard"].sort(key=lambda x: -x["money"])
            db["leaderboard"] = db["leaderboard"][:50]
            save_db(db)
            print(f"  🏆 Rekord: {name} — ${money:,}")
            self.send_json({"success": True})
            return

        self.send_json({"error": "Route nicht gefunden."}, 404)

    def do_DELETE(self):
        path = urlparse(self.path).path

        if path == "/api/account":
            db = load_db()
            uname, _ = self.get_user_from_token(db)
            if not uname:
                self.send_error_json("Nicht eingeloggt.", 401)
                return
            token = self.get_token()
            db["sessions"] = {t: u for t, u in db["sessions"].items() if u != uname}
            db["users"].pop(uname, None)
            save_db(db)
            print(f"  🗑 Account gelöscht: {uname}")
            self.send_json({"success": True})
            return

        if path.startswith("/api/save/"):
            slot = path.replace("/api/save/", "")
            db = load_db()
            uname, user = self.get_user_from_token(db)
            if not uname:
                self.send_error_json("Nicht eingeloggt.", 401)
                return
            if "saves" in db["users"][uname]:
                db["users"][uname]["saves"].pop(slot, None)
            save_db(db)
            self.send_json({"success": True})
            return

        if path == "/api/leaderboard":
            db = load_db()
            db["leaderboard"] = []
            save_db(db)
            self.send_json({"success": True})
            return

        self.send_json({"error": "Route nicht gefunden."}, 404)


# ─── START ──────────────────────────────────────────────────
START_TIME = time.time()

if __name__ == "__main__":
    local_ip = get_local_ip()
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    if not os.path.exists("index.html"):
        print("\n  ⚠️  WARNUNG: index.html nicht gefunden!")
        print("     Bitte game HTML umbenennen zu: index.html\n")

    server = http.server.HTTPServer(("0.0.0.0", PORT), GameHandler)

    print("\n")
    print("  ╔══════════════════════════════════════════════╗")
    print("  ║    🏢  BUSINESS EMPIRE SERVER v0.0.6         ║")
    print("  ╠══════════════════════════════════════════════╣")
    print(f"  ║  ✅ Server läuft!                             ║")
    print(f"  ║                                               ║")
    print(f"  ║  Dein PC:  http://localhost:{PORT}            ║")
    print(f"  ║  Netzwerk: http://{local_ip}:{PORT}      ║")
    print(f"  ║                                               ║")
    print(f"  ║  Andere PCs: Netzwerk-URL eingeben!           ║")
    print(f"  ║  Stoppen:    Strg+C drücken                   ║")
    print("  ╚══════════════════════════════════════════════╝")
    print("\n  📡 Warte auf Spieler...\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n  👋 Server gestoppt. Auf Wiedersehen!")
        server.shutdown()
