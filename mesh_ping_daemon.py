import os
import sys
import json
import socket
import time
import datetime

# Force UTF-8 stream handling on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

HOST = "127.0.0.1"
PEER_PORTS = {
    "ALPHA_NODE"  : 9001,
    "BRAVO_NODE"  : 9002,
    "CHARLIE_NODE": 9003,
    "DELTA_NODE"  : 9004,
    "STRESS_NODE" : 9005
}

def ping_peer(name, port):
    start = time.time()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.15)
        s.connect((HOST, port))
        s.close()
        rtt = (time.time() - start) * 1000
        return True, rtt
    except (ConnectionRefusedError, socket.timeout, OSError):
        return False, 0.0

def run_ping_daemon():
    print("=" * 65)
    print(" GARZA GLOBAL GRAVITON: P2P REAL-TIME PEER DISCOVERY DAEMON")
    print("=" * 65)
    print("\n[INIT] Executing 3-cycle pulse sweep across peer ports...\n")

    online_nodes = 0
    total_nodes = len(PEER_PORTS)

    for cycle in range(1, 4):
        print(f"--- PULSE CYCLE {cycle}/3 ---")
        cycle_online = 0
        for name, port in PEER_PORTS.items():
            is_alive, rtt = ping_peer(name, port)
            if is_alive:
                cycle_online += 1
                print(f"  + [{name}] Port {port} -> ONLINE | RTT: {rtt:.2f}ms")
            else:
                print(f"  - [{name}] Port {port} -> STANDBY / UNREACHABLE")
        
        if cycle_online > online_nodes:
            online_nodes = cycle_online
            
        time.sleep(0.2)

    print("\n" + "=" * 65)
    print(f" DAEMON SUMMARY: Peak Reachable Peers = {online_nodes}/{total_nodes}")
    print("=" * 65)

    # Log heartbeat state to ledger
    ledger_path = os.path.join("..", "04_Legal_and_IP", "sovereign_ledger.json")
    if os.path.exists(ledger_path):
        try:
            with open(ledger_path, "r", encoding="utf-8") as f:
                ledger = json.load(f)
            entry = {
                "event": "PEER_PING_DAEMON_SWEEP_COMPLETE",
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
                "peak_peers_online": online_nodes,
                "total_peers_scanned": total_nodes,
                "status": "PASS"
            }
            ledger.append(entry)
            with open(ledger_path, "w", encoding="utf-8") as f:
                json.dump(ledger, f, indent=2)
            print("[STATUS] Peer ping heartbeat logged to sovereign_ledger.json")
        except Exception as e:
            print(f"[WARNING] Could not update ledger: {e}")

    print("\n--- Peer Ping Daemon Sweep Complete ---")

if __name__ == "__main__":
    run_ping_daemon()