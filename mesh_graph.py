import os
import sys
import json
import socket
import time
import datetime

# Force UTF-8 encoding for standard streams on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

HOST = "127.0.0.1"
NODES = {
    "ALPHA_NODE"  : 9001,
    "BRAVO_NODE"  : 9002,
    "CHARLIE_NODE": 9003,
    "DELTA_NODE"  : 9004,
    "STRESS_NODE" : 9005
}

def check_node_status(port):
    start_time = time.time()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.1)
        s.connect((HOST, port))
        s.close()
        latency = (time.time() - start_time) * 1000
        return True, f"{latency:.1f}ms"
    except (ConnectionRefusedError, socket.timeout, OSError):
        return False, "OFFLINE"

def render_topology_graph():
    print("=" * 65)
    print(" GARZA GLOBAL GRAVITON: P2P MESH TOPOLOGY GRAPH VISUALIZER")
    print("=" * 65)
    print(f"\n[SCANNING] Probing local node sockets on host {HOST}...\n")

    node_states = {}
    online_count = 0

    for name, port in NODES.items():
        is_online, latency = check_node_status(port)
        node_states[name] = {"port": port, "online": is_online, "latency": latency}
        if is_online:
            online_count += 1

    # Render Terminal ASCII Graph
    print("                     +-----------------------+")
    print("                     |   MASTER MESH ROUTER  |")
    print("                     +-----------+-----------+")
    print("                                 |")
    print("         +-----------------------+-----------------------+")
    print("         |                       |                       |")

    a_status = "[ONLINE]" if node_states["ALPHA_NODE"]["online"] else "[STANDBY]"
    b_status = "[ONLINE]" if node_states["BRAVO_NODE"]["online"] else "[STANDBY]"
    c_status = "[ONLINE]" if node_states["CHARLIE_NODE"]["online"] else "[STANDBY]"

    print(f"  +------+------+         +------+------+         +------+------+")
    print(f"  | ALPHA NODE  |         | BRAVO NODE  |         | CHARLIE NODE|")
    print(f"  | Port: 9001  |         | Port: 9002  |         | Port: 9003  |")
    print(f"  | {a_status:<10}  |         | {b_status:<10}  |         | {c_status:<10}  |")
    print(f"  +------+------+         +------+------+         +------+------+")
    print("         |                       |                       |")
    print("         +-----------------------+-----------------------+")
    print("                                 |")

    d_status = "[ONLINE]" if node_states["DELTA_NODE"]["online"] else "[STANDBY]"
    s_status = "[ONLINE]" if node_states["STRESS_NODE"]["online"] else "[STANDBY]"

    print(f"                 +---------------+---------------+")
    print(f"                 | DELTA (9004)  | STRESS (9005) |")
    print(f"                 | {d_status:<11} | {s_status:<11} |")
    print(f"                 +---------------+---------------+")

    print("\n" + "=" * 65)
    print(f" TOPOLOGY SUMMARY: {online_count}/{len(NODES)} ACTIVE SOCKET LISTENERS DETECTED")
    print("=" * 65)

    # Log Topology Snapshot to Ledger
    ledger_path = os.path.join("..", "04_Legal_and_IP", "sovereign_ledger.json")
    if os.path.exists(ledger_path):
        try:
            with open(ledger_path, "r", encoding="utf-8") as f:
                ledger = json.load(f)
            entry = {
                "event": "MESH_TOPOLOGY_GRAPH_SCANNED",
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
                "nodes_scanned": len(NODES),
                "nodes_online": online_count,
                "status": "PASS"
            }
            ledger.append(entry)
            with open(ledger_path, "w", encoding="utf-8") as f:
                json.dump(ledger, f, indent=2)
            print("[STATUS] Mesh graph state logged to sovereign_ledger.json")
        except Exception as e:
            print(f"[WARNING] Could not update ledger: {e}")

    print("\n--- Mesh Topology Graph Sweep Complete ---")

if __name__ == "__main__":
    render_topology_graph()