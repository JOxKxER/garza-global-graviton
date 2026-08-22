import os
import sys
import json
import socket
import threading
import time
import hashlib
import datetime

HOST = "127.0.0.1"
PRIMARY_PORT = 9002   # Simulated Offline Target
FALLBACK_PORT = 9004  # Dynamic Failover Target

def calculate_hash(data_str):
    return hashlib.sha256(data_str.encode('utf-8')).hexdigest()

def fallback_server_thread(stop_event):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, FALLBACK_PORT))
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
                    "node": "DELTA_FALLBACK_NODE",
                    "status": "ACK",
                    "shard_id": shard_id,
                    "integrity": status
                })
                conn.sendall(response.encode('utf-8'))
            conn.close()
        except socket.timeout:
            continue
        except Exception as e:
            print(f"[FALLBACK SERVER ERROR] {e}")
            break

    server.close()

def run_failover_router_demo():
    print("=" * 65)
    print(" GARZA GLOBAL GRAVITON: DYNAMIC PORT FAILOVER ROUTER")
    print("=" * 65)

    stop_event = threading.Event()
    fallback_thread = threading.Thread(target=fallback_server_thread, args=(stop_event,))
    fallback_thread.start()
    
    print(f"\n[INIT] Secondary Fallback Node online at tcp://{HOST}:{FALLBACK_PORT}")
    time.sleep(0.5)

    shard_id = "0x99C4"
    raw_data = "DYNAMIC_FAILOVER_VECTOR_SHARD_PAYLOAD"
    checksum = calculate_hash(raw_data)
    
    packet = {
        "shard_id": shard_id,
        "raw_data": raw_data,
        "checksum": checksum
    }

    # Attempting transmission to dark primary port (9002)
    print(f"\n[DISPATCHER] Attempting primary transmission to tcp://{HOST}:{PRIMARY_PORT}...")
    
    transmitted_successfully = False
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(1.0)
        client.connect((HOST, PRIMARY_PORT))
        client.sendall(json.dumps(packet).encode('utf-8'))
        client.close()
        transmitted_successfully = True
    except (ConnectionRefusedError, socket.timeout, OSError):
        print(f"  └─ [WARNING] Primary port {PRIMARY_PORT} UNREACHABLE! Dynamic failover triggered.")

    # Execute Failover Redirect
    if not transmitted_successfully:
        print(f"[DISPATCHER] Rerouting Shard [{shard_id}] to Fallback Node (tcp://{HOST}:{FALLBACK_PORT})...")
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((HOST, FALLBACK_PORT))
            client.sendall(json.dumps(packet).encode('utf-8'))
            
            resp = client.recv(1024).decode('utf-8')
            payload_ack = json.loads(resp)
            client.close()
            
            print(f"  └─ [SUCCESS] ACK received from {payload_ack['node']} -> Integrity: {payload_ack['integrity']}")
            
            # Log Failover to Ledger
            ledger_path = os.path.join("..", "04_Legal_and_IP", "sovereign_ledger.json")
            if os.path.exists(ledger_path):
                try:
                    with open(ledger_path, "r") as f:
                        ledger = json.load(f)
                    entry = {
                        "event": "DYNAMIC_SOCKET_FAILOVER_SUCCESS",
                        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
                        "primary_port_failed": PRIMARY_PORT,
                        "fallback_port_used": FALLBACK_PORT,
                        "shard_id": shard_id,
                        "status": "REROUTED_AND_VERIFIED"
                    }
                    ledger.append(entry)
                    with open(ledger_path, "w") as f:
                        json.dump(ledger, f, indent=2)
                    print("[STATUS] Failover event logged to sovereign_ledger.json")
                except Exception as e:
                    print(f"[WARNING] Could not update ledger: {e}")

        except Exception as e:
            print(f"  └─ [ERROR] Fallback transmission failed: {e}")

    stop_event.set()
    fallback_thread.join()

    print("\n--- Dynamic Failover Router Sweep Complete ---")

if __name__ == "__main__":
    run_failover_router_demo()