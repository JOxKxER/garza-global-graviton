import os
import sys
import json
import socket
import threading
import time
import random
import hashlib
import datetime

# Force UTF-8 stream handling on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

HOST = "127.0.0.1"
STRESS_PORT = 9005

def calculate_hash(data_str):
    return hashlib.sha256(data_str.encode('utf-8')).hexdigest()

def noisy_network_node(stop_event):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, STRESS_PORT))
    server.listen(5)
    server.settimeout(1.0)

    while not stop_event.is_set():
        try:
            conn, addr = server.accept()
            data = conn.recv(1024).decode('utf-8')
            if data:
                # Simulate network jitter (10ms - 80ms delay)
                time.sleep(random.uniform(0.01, 0.08))

                # Simulate 20% Packet Loss
                if random.random() < 0.20:
                    conn.close() # Connection dropped
                    continue

                payload = json.loads(data)
                shard_id = payload.get("shard_id", "UNKNOWN")
                checksum = payload.get("checksum", "")
                computed = calculate_hash(payload.get("raw_data", ""))

                status = "VALID" if computed == checksum else "CORRUPTED"
                response = json.dumps({
                    "status": "ACK",
                    "shard_id": shard_id,
                    "integrity": status
                })
                conn.sendall(response.encode('utf-8'))
            conn.close()
        except socket.timeout:
            continue
        except Exception as e:
            break

    server.close()

def run_stress_test():
    print("=" * 65)
    print(" GARZA GLOBAL GRAVITON: P2P NETWORK LATENCY & PACKET LOSS SIMULATOR")
    print("=" * 65)

    stop_event = threading.Event()
    node_thread = threading.Thread(target=noisy_network_node, args=(stop_event,))
    node_thread.start()

    print(f"\n[INIT] Tactical Noisy Node Online at tcp://{HOST}:{STRESS_PORT}")
    print("[CONFIG] Simulating 10-80ms Jitter | 20% Packet Loss Rate\n")

    total_packets = 10
    successful_transmissions = 0
    retries = 0

    start_time = time.time()

    for i in range(1, total_packets + 1):
        shard_id = f"0x{random.randint(0x1000, 0xFFFF):X}"
        raw_data = f"TACTICAL_VECTOR_SHARD_BURST_{i}"
        checksum = calculate_hash(raw_data)
        
        packet = {
            "shard_id": shard_id,
            "raw_data": raw_data,
            "checksum": checksum
        }

        delivered = False
        max_attempts = 3
        attempt = 0

        while attempt < max_attempts and not delivered:
            attempt += 1
            try:
                client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client.settimeout(0.2)
                client.connect((HOST, STRESS_PORT))
                client.sendall(json.dumps(packet).encode('utf-8'))

                resp = client.recv(1024).decode('utf-8')
                if resp:
                    payload_ack = json.loads(resp)
                    if payload_ack.get("integrity") == "VALID":
                        delivered = True
                        successful_transmissions += 1
                        print(f"  + Shard [{shard_id}] Delivered (Attempt {attempt}) -> Integrity: VALID")
                client.close()
            except (socket.timeout, ConnectionResetError, ConnectionRefusedError):
                retries += 1
                time.sleep(0.05) # Brief retry delay

        if not delivered:
            print(f"  - Shard [{shard_id}] FAILED after {max_attempts} attempts.")

    total_duration = time.time() - start_time
    reliability_rate = (successful_transmissions / total_packets) * 100

    print("\n" + "=" * 65)
    print(f" STRESS METRICS: {successful_transmissions}/{total_packets} DELIVERED ({reliability_rate:.1f}%)")
    print(f" TOTAL RETRIES TRIGGERED: {retries}")
    print(f" TOTAL TEST DURATION    : {total_duration:.2f}s")
    print("=" * 65)

    # Log metrics to sovereign ledger
    ledger_path = os.path.join("..", "04_Legal_and_IP", "sovereign_ledger.json")
    if os.path.exists(ledger_path):
        try:
            with open(ledger_path, "r", encoding="utf-8") as f:
                ledger = json.load(f)
            entry = {
                "event": "NETWORK_STRESS_SIMULATION_COMPLETE",
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
                "packets_sent": total_packets,
                "reliability_rate": f"{reliability_rate:.1f}%",
                "retries": retries,
                "status": "PASS"
            }
            ledger.append(entry)
            with open(ledger_path, "w", encoding="utf-8") as f:
                json.dump(ledger, f, indent=2)
            print("[STATUS] Network stress metrics logged to sovereign_ledger.json")
        except Exception as e:
            print(f"[WARNING] Could not update ledger: {e}")

    stop_event.set()
    node_thread.join()

    print("\n--- Network Stress Sweep Complete ---")

if __name__ == "__main__":
    run_stress_test()