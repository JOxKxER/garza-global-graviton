import asyncio
import hashlib
import json
import os
import sys

WORKER_ID = f"node-{os.getpid()}"

async def run_worker(host="127.0.0.1", port=8765):
    print(f"[{WORKER_ID}] Connecting to Topology Coordinator at {host}:{port}...")
    while True:
        try:
            reader, writer = await asyncio.open_connection(host, port)
            print(f"[{WORKER_ID}] Connected to Shard Coordinator. Listening for workloads.")
            
            while True:
                data = await reader.readline()
                if not data:
                    break
                task = json.loads(data.decode())
                order_id = task.get("order_id", "unknown")
                elements = task.get("elements", 0)
                
                # Compute parallel deterministic leaf proof
                proof = hashlib.sha256(f"{order_id}_{elements}_{WORKER_ID}".encode()).hexdigest()
                
                response = {
                    "worker_id": WORKER_ID,
                    "order_id": order_id,
                    "processed_elements": elements,
                    "shard_proof": proof,
                    "status": "SETTLED"
                }
                writer.write((json.dumps(response) + "\n").encode())
                await writer.drain()
        except ConnectionRefusedError:
            await asyncio.sleep(2)
        except Exception as e:
            await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(run_worker())
