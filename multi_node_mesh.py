import os
import sys
import json
import socket
import threading
import time
import hashlib
import datetime

HOST = "127.0.0.1"
NODES_CONFIG = {
    "ALPHA_NODE": 9001,
    "BRAVO_NODE": 9002,
    "CHARLIE_NODE": 9003
}

def calculate_hash(data_str):
    return hashlib.sha256(data_str.encode('utf-8')).hexdigest()

def node_server_thread(node_name, port, stop_event):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, port))
    server.listen(5)
    server.settimeout(1.0)

    while not stop_event.is_set():
        try:
            conn, addr = server.accept()
            data = conn.recv(1024).decode('utf-8')
            if data:
                payload = json.loads(data)
                shard_id = payload.get("shard_id", "UNKNOWN")
                checksum = payload.get("checksum", "")
                computed = calculate_hash(payload.get("raw_data", ""))
                
                status = "VALID" if computed == checksum else "CORRUPTED"
                response = json.dumps({
                    "node": node_name,
                    "status": "ACK",
                    "shard_id": shard_id,
                    "integrity": status
                })
                conn.sendall(response.encode('utf-8'))
            conn.close()
        except socket.timeout:
            continue
        except Exception as e:
            print(f"[{node_name} ERROR] {e}")
            break

    server.close()

def run_multi_node_broadcast():
    print("=" * 65)
    print(" GARZA GLOBAL GRAVITON: MULTI-NODE BROADCAST MESH ENGINE")
    print("=" * 65)

    stop_event = threading.Event()
    threads = []

    # Spin up 3 listening node threads
    print("\n[INIT] Starting Multi-Node Local Socket Listeners...")
    for node_name, port in NODES_CONFIG.items():
        t = threading.Thread(target=node_server_thread, args=(node_name, port, stop_event))
        t.start()
        threads.append(t)
        print(f"  └─ {node_name} listening on tcp://{HOST}:{port}")

    time.sleep(0.5)

    # Broadcast Shard to all 3 nodes
    shard_id = "0x88F2"
    raw_data = "FRACTAL_SHARD_VECTOR_CONCURRENT_BROADCAST_PAYLOAD"
    checksum = calculate_hash(raw_data)
    
    packet = {
        "shard_id": shard_id,
        "raw_data": raw_data,
        "checksum": checksum
    }

    print(f"\n[BROADCASTER] Transmitting Shard [{shard_id}] across 3 active sockets...")
    
    ack_count = 0
    for node_name, port in NODES_CONFIG.items():
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((HOST, port))
            client.sendall(json.dumps(packet).encode('utf-8'))
            
            resp = client.recv(1024).decode('utf-8')
            payload_ack = json.loads(resp)
            client.close()
            
            print(f"  » ACK from {node_name} ({HOST}:{port}) -> {payload_ack['integrity']}")
            if payload_ack.get("integrity") == "VALID":
                ack_count += 1
        except Exception as e:
            print(f"  » Failed to transmit to {node_name}: {e}")

    # Log execution
    if ack_count == len(NODES_CONFIG):
        print(f"\n[SUCCESS] 3/3 Node Sockets Acknowledged Payload Integrity!")
        ledger_path = os.path.join("..", "04_Legal_and_IP", "sovereign_ledger.json")
        if os.path.exists(ledger_path):
            try:
                with open(ledger_path, "r") as f:
                    ledger = json.load(f)
                entry = {
                    "event": "MULTI_NODE_SOCKET_BROADCAST_COMPLETE",
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
                    "nodes_acknowledged": ack_count,
                    "status": "PASS"
                }
                ledger.append(entry)
                with open(ledger_path, "w") as f:
                    json.dump(ledger, f, indent=2)
                print("[STATUS] Multi-node broadcast logged to sovereign_ledger.json")
            except Exception as e:
                print(f"[WARNING] Could not update ledger: {e}")

    # Shutdown threads cleanly
    stop_event.set()
    for t in threads:
        t.join()

    print("\n--- Multi-Node Broadcast Sweep Complete ---")

if __name__ == "__main__":
    run_multi_node_broadcast()