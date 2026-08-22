import asyncio
import uvicorn
import sqlite3
import json
import hashlib
from src.api import app, DB_PATH

def enable_wal():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.commit()
    conn.close()

connected_workers = []

async def handle_worker(reader, writer):
    addr = writer.get_extra_info('peername')
    print(f'[COORDINATOR] Worker shard attached from {addr}')
    worker_handle = {'reader': reader, 'writer': writer, 'addr': addr}
    connected_workers.append(worker_handle)
    try:
        while True:
            data = await reader.readline()
            if not data:
                break
            payload = json.loads(data.decode())
            print(f"[COORDINATOR] Shard receipt: Node {payload.get('worker_id')} settled {payload.get('order_id')} ({payload.get('processed_elements'):,} elements) | Proof: {payload.get('shard_proof', '')[:12]}...")
    except Exception:
        pass
    finally:
        print(f'[COORDINATOR] Worker {addr} disconnected.')
        if worker_handle in connected_workers:
            connected_workers.remove(worker_handle)

async def start_tcp_coordinator(host='0.0.0.0', port=8765):
    server = await asyncio.start_server(handle_worker, host, port)
    print(f'[*] Non-Blocking Shard Manager active on TCP port {port}')
    async with server:
        await server.serve_forever()

async def main():
    enable_wal()
    config = uvicorn.Config(app, host='0.0.0.0', port=8000, log_level='info')
    server = uvicorn.Server(config)
    
    await asyncio.gather(
        server.serve(),
        start_tcp_coordinator()
    )

if __name__ == '__main__':
    asyncio.run(main())
