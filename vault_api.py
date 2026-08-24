"""
vault_api.py - Lightweight REST API Gateway for Game Servers & Tournament Bots
Provides endpoints for blacklist lookups, telemetry streaming, and automated match finalization.
Run with: python vault_api.py
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import sqlite3
import urllib.parse
from datetime import datetime
import os

DB_FILE = "vault.db"
API_PORT = 8000

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

class VaultAPIHandler(BaseHTTPRequestHandler):
    def _send_json(self, status_code, data):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))

    def do_OPTIONS(self):
        self._send_json(200, {"status": "OK"})

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # 1. Health Check
        if path == "/api/v1/health":
            self._send_json(200, {
                "status": "HEALTHY",
                "service": "Server Vault API Sentinel",
                "timestamp_utc": datetime.utcnow().isoformat()
            })

        # 2. Player Gatekeeper Check (Whitelisted vs Blacklisted)
        elif path == "/api/v1/auth/player-check":
            gamer_tag = query.get("gamer_tag", [""])[0]
            steam_id = query.get("steam_id", [""])[0]
            hw_fingerprint = query.get("hw_fingerprint", [""])[0]

            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                SELECT * FROM banned_players 
                WHERE gamer_tag = ? OR (steam_id != '' AND steam_id = ?) OR (hardware_fingerprint != '' AND hardware_fingerprint = ?)
                """, (gamer_tag, steam_id, hw_fingerprint))
                ban = cursor.fetchone()

                if ban:
                    self._send_json(403, {
                        "authorized": False,
                        "action": "KICK_AND_BLOCK",
                        "reason": f"Active Blacklist: {ban['violation_type']}",
                        "evidence_hash": ban["evidence_hash"]
                    })
                else:
                    self._send_json(200, {
                        "authorized": True,
                        "action": "ALLOW_CONNECTION",
                        "gamer_tag": gamer_tag,
                        "clean_standing": True
                    })

        # 3. Active Lobbies Feed
        elif path == "/api/v1/lobbies":
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM public_lobbies ORDER BY created_at DESC")
                lobbies = [dict(row) for row in cursor.fetchall()]
                for l in lobbies:
                    l["players"] = json.loads(l["players"])
                self._send_json(200, {"count": len(lobbies), "lobbies": lobbies})

        else:
            self._send_json(404, {"error": "Endpoint not found"})

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        try:
            payload = json.loads(body) if body else {}
        except Exception:
            self._send_json(400, {"error": "Invalid JSON payload"})
            return

        # 1. Report Live Security Anomaly from Dedicated Server Engine
        if path == "/api/v1/telemetry/report-anomaly":
            node_id = payload.get("node_id", "unknown-node")
            node_name = payload.get("node_name", "Game Instance")
            vector = payload.get("vector", "Unspecified Heuristic Trigger")
            action = payload.get("action_taken", "Logged")
            confidence = payload.get("confidence", "99.0%")

            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                INSERT INTO security_events (timestamp, node_id, node_name, vector, action_taken, confidence)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), node_id, node_name, vector, action, confidence))
                conn.commit()

            self._send_json(201, {"status": "LOGGED_TO_VAULT", "recorded_at": datetime.utcnow().isoformat()})

        # 2. Token Transfer / Payout Endpoint
        elif path == "/api/v1/wallet/credit":
            username = payload.get("username")
            amount = payload.get("amount", 0)
            reason = payload.get("reason", "API Reward Grant")

            if not username or amount <= 0:
                self._send_json(400, {"error": "Invalid username or amount"})
                return

            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET token_balance = token_balance + ? WHERE username = ?", (amount, username))
                cursor.execute("""
                INSERT INTO token_transactions (tx_id, username, amount, type, description)
                VALUES (?, ?, ?, 'API_CREDIT', ?)
                """, (f"tx-{os.urandom(4).hex()}", username, amount, reason))
                conn.commit()

            self._send_json(200, {"status": "WALLET_CREDITED", "user": username, "amount_credited": amount})

        else:
            self._send_json(404, {"error": "Endpoint not found"})

def run_api_server():
    server_address = ('', API_PORT)
    httpd = HTTPServer(server_address, VaultAPIHandler)
    print("=" * 65)
    print(f"🚀 SERVER VAULT REST API GATEWAY RUNNING ON PORT {API_PORT}")
    print(f"   • Health Check:     GET  http://localhost:{API_PORT}/api/v1/health")
    print(f"   • Gatekeeper Check: GET  http://localhost:{API_PORT}/api/v1/auth/player-check?gamer_tag=Exploiter#4040")
    print(f"   • Lobby Feed:       GET  http://localhost:{API_PORT}/api/v1/lobbies")
    print(f"   • Report Anomaly:   POST http://localhost:{API_PORT}/api/v1/telemetry/report-anomaly")
    print("=" * 65)
    httpd.serve_forever()

if __name__ == "__main__":
    try:
        run_api_server()
    except KeyboardInterrupt:
        print("\n[INFO] API Gateway stopped by user.")