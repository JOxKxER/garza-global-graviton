"""
client_sender.py - Simulated Game Client Telemetry Streamer
Streams continuous UDP packets to the server anti-cheat daemon.
"""

import socket
import json
import time
import random

UDP_IP = "127.0.0.1"
UDP_PORT = 27015

def run_client():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(f"🎮 Telemetry Client Started. Streaming to UDP {UDP_PORT}...")
    
    player_id = "Player_Apex_01"
    
    try:
        while True:
            # Simulate normal or occasional anomalous behavior
            is_cheating = random.random() < 0.05 # 5% chance of test anomaly
            
            packet = {
                "server_name": "Garza Global Graviton Arena #1",
                "player_id": player_id,
                "velocity": round(random.uniform(1.0, 2.5) if not is_cheating else 5.8, 2),
                "aim_delta": round(random.uniform(10.0, 45.0) if not is_cheating else 145.0, 2),
                "memory_hook": is_cheating and random.random() > 0.5
            }
            
            sock.sendto(json.dumps(packet).encode('utf-8'), (UDP_IP, UDP_PORT))
            print(f"📡 Sent telemetry: Vel={packet['velocity']}, AimDelta={packet['aim_delta']}")
            
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\nClient stopped.")

if __name__ == "__main__":
    run_client()