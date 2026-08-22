import socket
import json
import time
import hashlib
import sys

WORKER_ID = f"Node_Worker_{sys.argv[1] if len(sys.argv) > 1 else '01'}"
COORDINATOR_HOST = "127.0.0.1"
COORDINATOR_PORT = 9000

def compute_chunk(data_chunk, scale_factor):
    """Simulate mathematical vector computation & cryptographic verification"""
    start_time = time.perf_counter()
    count = data_chunk.get("count", 100000)
    
    # Mathematical transformation workload
    dummy_checksum = 0
    for i in range(min(count, 50000)):
        dummy_checksum += int((i * scale_factor) % 256)
        
    chunk_hash = hashlib.sha256(f"{dummy_checksum}_{count}".encode()).hexdigest()
    elapsed = (time.perf_counter() - start_time) * 1000
    
    return {
        "worker_id": WORKER_ID,
        "processed_elements": count,
        "execution_time_ms": round(elapsed, 2),
        "chunk_merkle_leaf": chunk_hash
    }

def main():
    print(f"[{WORKER_ID}] Initializing Distributed Compute Worker...")
    print(f"[{WORKER_ID}] Connecting to Coordinator at {COORDINATOR_HOST}:{COORDINATOR_PORT}...")
    
    # Standalone mock worker listening for coordinator dispatch
    while True:
        try:
            print(f"[{WORKER_ID}] Worker ready. Polling cluster tasks...")
            time.sleep(3)
            # Simulated chunk processing
            result = compute_chunk({"count": 150000}, 2.0)
            print(f"[{WORKER_ID}] Settled Sub-Shard: {result['processed_elements']:,} elements in {result['execution_time_ms']}ms | Leaf: {result['chunk_merkle_leaf'][:16]}...")
        except KeyboardInterrupt:
            print(f"\n[{WORKER_ID}] Worker shutting down.")
            break

if __name__ == "__main__":
    main()
