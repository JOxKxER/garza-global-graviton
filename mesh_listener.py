import os
import sys
import json
import socket
import threading
import time
import hashlib
import datetime

HOST = "127.0.0.1"
LISTEN_PORT = 9001

def calculate_hash(data_str):
    return hashlib.sha256(data_str.encode('utf-8')).hexdigest()

def start_server_node(stop_event):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, LISTEN_PORT))
    server.listen(5)
    server.settimeout(1.0)
    
    print(f"[NODE SERVER] Listening on tcp://{HOST}:{LISTEN_PORT}...")

    while not stop_event.is_set():
        try:
            conn, addr = server.accept()
            data = conn.recv(1024).decode('utf-8')
            if data:
                payload = json.loads(data)
                shard_id = payload.get("shard_id", "UNKNOWN")
                checksum = payload.get("checksum", "")
                
                # Verify payload checksum
                computed = calculate_hash(payload.get("raw_data", ""))
                status = "VALID" if computed == checksum else "CORRUPTED"
                
                # Send acknowledgment
                response = json.dumps({"status": "ACK", "shard_id": shard_id, "integrity": status})
                conn.sendall(response.encode('utf-8'))
            conn.close()
        except socket.timeout:
            continue
        except Exception as e:
            print(f"[NODE SERVER ERROR] {e}")
            break

    server.close()
    print("[NODE SERVER] Socket closed cleanly.")

def run_mesh_listener_demo():
    print("=" * 65)
    print(" GARZA GLOBAL GRAVITON: P2P LOCAL SOCKET MESH ENGINE")
    print("=" * 65)

    stop_event = threading.Event()
    server_thread = threading.Thread(target=start_server_node, args=(stop_event,))
    server_thread.start()

    time.sleep(0.5)

    # Simulate Client Sending Vector Shard Packet Over Socket
    print("\n[CLIENT DISPATCHER] Packaging vector shard payload...")
    raw_payload_data = "VECTOR_SHARD_CHUNK_77A8_FRACTAL_ENCODED"
    payload_hash = calculate_hash(raw_payload_data)

    packet = {
        "shard_id": "0x77A8",
        "sender": "ALPHA_NODE",
        "raw_data": raw_payload_data,
        "checksum": payload_hash
    }

    try:
        print(f"[CLIENT DISPATCHER] Connecting to tcp://{HOST}:{LISTEN_PORT}...")
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((HOST, LISTEN_PORT))
        client.sendall(json.dumps(packet).encode('utf-8'))

        ack_data = client.recv(1024).decode('utf-8')
        ack_payload = json.loads(ack_data)
        client.close()

        print(f"[CLIENT DISPATCHER] ACK Received: {ack_payload}")

        if ack_payload.get("integrity") == "VALID":
            print("\n[SUCCESS] Socket transmission and cryptographic handshake verified!")
            
            # Log event to sovereign ledger
            ledger_path = os.path.join("..", "04_Legal_and_IP", "sovereign_ledger.json")
            if os.path.exists(ledger_path):
                try:
                    with open(ledger_path, "r") as f:
                        ledger = json.load(f)
                    entry = {
                        "event": "P2P_SOCKET_HANDSHAKE_COMPLETE",
                        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
                        "socket": f"{HOST}:{LISTEN_PORT}",
                        "shard_id": ack_payload.get("shard_id"),
                        "status": "VERIFIED_COMPLIANT"
                    }
                    ledger.append(entry)
                    with open(ledger_path, "w") as f:
                        json.dump(ledger, f, indent=2)
                    print("[STATUS] Event logged to sovereign_ledger.json")
                except Exception as e:
                    print(f"[WARNING] Could not update ledger: {e}")

    except Exception as e:
        print(f"[CLIENT ERROR] Transmission failed: {e}")

    finally:
        stop_event.set()
        server_thread.join()

    print("\n--- P2P Socket Mesh Sweep Complete ---")

if __name__ == "__main__":
    run_mesh_listener_demo()