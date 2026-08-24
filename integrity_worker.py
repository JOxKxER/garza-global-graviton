"""
integrity_worker.py - Real-Time UDP Anti-Cheat Listener & Discord Notifier
Captures live telemetry, applies active DB heuristics, and dispatches webhook alerts.
"""

import time
import socket
import json
import urllib.request
import urllib.error
from datetime import datetime
import db_manager as db

UDP_IP = "127.0.0.1"
UDP_PORT = 27015

def send_discord_alert(webhook_url, node_name, player_id, vector, action, confidence):
    if not webhook_url or not webhook_url.startswith("http"):
        return

    payload = {
        "username": "Server Vault Anti-Cheat",
        "avatar_url": "https://img.icons8.com/color/512/shield.png",
        "embeds": [
            {
                "title": "🚨 Security Vector Enforced",
                "color": 15548997,
                "fields": [
                    {"name": "Server Node", "value": str(node_name), "inline": True},
                    {"name": "Player Flagged", "value": f"`{player_id}`", "inline": True},
                    {"name": "Confidence", "value": f"**{confidence}**", "inline": True},
                    {"name": "Detection Vector", "value": str(vector), "inline": False},
                    {"name": "Automated Action", "value": f"```{action}```", "inline": False}
                ],
                "footer": {"text": "Deterministic Integrity Lock • Live Stream"},
                "timestamp": datetime.utcnow().isoformat()
            }
        ]
    }

    try:
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'User-Agent': 'IntegrityWorker/1.0'}
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            pass
    except Exception as e:
        print(f"[WARN] Discord webhook dispatch failed: {e}")

def main():
    print("=" * 60)
    print(f"🛡️  LIVE INTEGRITY DAEMON STARTED ON UDP {UDP_PORT}")
    print("=" * 60)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Enable address reuse to prevent WinError 10048 if restarted quickly
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((UDP_IP, UDP_PORT))
    sock.setblocking(False)

    while True:
        policies = db.get_policies()
        vel_limit = policies.get("velocity_deviation_sigma", 2.2)
        aim_limit = policies.get("aim_vector_threshold_deg_per_ms", 65.0)
        auto_kick = bool(policies.get("auto_kick_memory_hook", 1))
        discord_url = policies.get("discord_webhook_url", "")

        try:
            data, addr = sock.recvfrom(1024)
            packet = json.loads(data.decode('utf-8'))

            player_id = packet.get("player_id", "Unknown")
            velocity = packet.get("velocity", 0.0)
            aim_delta = packet.get("aim_delta", 0.0)
            memory_flag = packet.get("memory_hook", False)
            node_name = packet.get("server_name", "Live Socket Server")

            detected_vector = None
            action = None

            if memory_flag and auto_kick:
                detected_vector = "Direct Memory Injection Hook Detected"
                action = f"Terminated Player {player_id} (Hard Kick)"
            elif velocity > vel_limit and policies.get("server_authoritative_position", 1):
                detected_vector = f"Velocity Anomaly: {velocity} > {vel_limit} sigma"
                action = f"Desynced Player {player_id} (Anti-Speedhack)"
            elif aim_delta > aim_limit and policies.get("sub_tick_packet_scan", 1):
                detected_vector = f"Aim Snapping Vector: {aim_delta}°/ms > {aim_limit}°/ms"
                action = f"Flagged Player {player_id} (Aimbot Path Snapping)"

            if detected_vector:
                db.log_security_event(
                    node_id="Local-Test-Node",
                    node_name=node_name,
                    vector=detected_vector,
                    action=action,
                    confidence="99.9%"
                )
                print(f"🚨 [DB LOGGED] {player_id} -> {detected_vector} | {action}")
                send_discord_alert(discord_url, node_name, player_id, detected_vector, action, "99.9%")
            else:
                print(f"✅ [CLEAN] Packet from {player_id} processed safely.")

        except BlockingIOError:
            time.sleep(0.05)
        except json.JSONDecodeError:
            print("⚠️ [WARN] Received malformed network packet.")

if __name__ == "__main__":
    main()