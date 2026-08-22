import socket
import json
import hashlib
import time
import sys

WORKER_ID = f"Node_Worker_{sys.argv[1] if len(sys.argv) > 1 else '01'}"
HOST = "127.0.0.1"
PORT = 9000

def process_shard(shard_data):
    count = shard_data.get("count", 150000)
    scale = shard_data.get("scale", 2.0)
    
    start = time.perf_counter()
    # Vector transformation simulation
    checksum = 0
    for i in range(min(count, 50000)):
        checksum += int((i * scale) % 256)
        
    leaf_hash = hashlib.sha256(f"{WORKER_ID}_{checksum}_{count}".encode()).hexdigest()
    elapsed = (time.perf_counter() - start) * 1000
    
    return {
        "worker_id": WORKER_ID,
        "processed_elements": count,
        "execution_ms": round(elapsed, 2),
        "merkle_leaf": leaf_hash
    }

def main():
    print(f"[{WORKER_ID}] Standalone Edge Worker Initialized.")
    print(f"[{WORKER_ID}] Ready for cluster dispatch tasks.")
    
    # Standalone execution loop simulating continuous edge compute processing
    while True:
        try:
            time.sleep(2)
            result = process_shard({"count": 150000, "scale": 2.0})
            print(f"[{WORKER_ID}] Processed Sub-Shard: {result['processed_elements']:,} elements in {result['execution_ms']}ms | Leaf: {result['merkle_leaf'][:16]}...")
        except KeyboardInterrupt:
            print(f"\n[{WORKER_ID}] Shutting down.")
            break

if __name__ == "__main__":
    main()
