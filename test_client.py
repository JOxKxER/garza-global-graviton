"""
test_client.py - Synthetic Game Client Simulator
Sends UDP telemetry packets to trigger the anti-cheat listener.
"""
import socket
import json
import time

UDP_IP = "127.0.0.1"
UDP_PORT = 27015

print("🎮 Game Client Simulator Started...")
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def send_telemetry(player, velocity, aim_delta, hook=False):
    packet = {
        "server_name": "Garza Global Test Server",
        "player_id": player,
        "velocity": velocity,
        "aim_delta": aim_delta,
        "memory_hook": hook
    }
    msg = json.dumps(packet).encode('utf-8')
    sock.sendto(msg, (UDP_IP, UDP_PORT))
    print(f"Sent packet for {player}")
    time.sleep(1.5)

# 1. Normal Player (Clean)
send_telemetry("Player_Clean", velocity=1.2, aim_delta=30.0)

# 2. Speedhacker (High Velocity)
send_telemetry("Player_Speedhacker", velocity=5.5, aim_delta=20.0)

# 3. Aimbot User (Instant aim snap)
send_telemetry("Player_Aimbot", velocity=1.0, aim_delta=150.0)

# 4. Memory Injector (Cheating software detected)
send_telemetry("Player_Injector", velocity=0.5, aim_delta=10.0, hook=True)

print("Transmission complete.")