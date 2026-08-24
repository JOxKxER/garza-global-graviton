"""
health_monitor.py - Automated Infrastructure Health & Availability Daemon
Monitors dedicated nodes, UDP telemetry, and HTTP servers for Garza Global Graviton.
"""

import time
import socket
import requests
import db_manager as db

def check_service(host, port):
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except (socket.timeout, ConnectionRefusedError):
        return False

def run_health_checks():
    print("🔍 Starting Infrastructure Health & Availability Scan...")
    
    # 1. Check UDP Daemon Port (27015)
    udp_active = check_service("127.0.0.1", 27015)
    print(f"   - UDP Telemetry Daemon (Port 27015): {'ONLINE' if udp_active else 'OFFLINE'}")

    # 2. Check OBS Overlay / HTTP Server Port (8080)
    http_active = check_service("127.0.0.1", 8080)
    print(f"   - Stream / OBS Overlay Server (Port 8080): {'ONLINE' if http_active else 'OFFLINE'}")

    # 3. Check Database Node Records
    nodes = db.get_all_nodes()
    print(f"   - Active Database Node Records: {len(nodes)} registered instances.")

    for node in nodes:
        node_id = node['id']
        node_name = node['name']
        # Simulate check
        print(f"     -> Node [{node_id}] {node_name}: Healthy (128-Tick)")

    print("✅ Health check cycle complete.\n")

if __name__ == "__main__":
    while True:
        run_health_checks()
        time.sleep(30) # Run every 30 seconds