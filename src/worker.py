import asyncio
import ssl
import json
import struct
import time
import hashlib
from typing import Dict, List, Tuple, Optional
import numpy as np

from src.core import MerkleTree

def hash_array_block(arr: np.ndarray) -> str:
    return hashlib.sha256(arr.tobytes()).hexdigest()

HEADER_STRUCT = "!I"

async def send_bytes(writer: asyncio.StreamWriter, data: bytes):
    header = struct.pack(HEADER_STRUCT, len(data))
    writer.write(header + data)
    await writer.drain()

async def recv_bytes(reader: asyncio.StreamReader) -> Optional[bytes]:
    try:
        header = await reader.readexactly(4)
        msg_len = struct.unpack(HEADER_STRUCT, header)[0]
        data = await reader.readexactly(msg_len)
        return data
    except (asyncio.IncompleteReadError, ConnectionResetError, Exception):
        return None

class AsyncNetworkCoordinator:
    def __init__(self, host: str = "127.0.0.1", port: int = 8765, ssl_context: Optional[ssl.SSLContext] = None):
        self.host = host
        self.port = port
        self.ssl_context = ssl_context
        self.server = None
        self.workers: Dict[str, Tuple[asyncio.StreamReader, asyncio.StreamWriter]] = {}

    async def start_server(self):
        self.server = await asyncio.start_server(
            self._handle_client,
            self.host,
            self.port,
            ssl=self.ssl_context
        )

    async def stop_server(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        for w_id, (_, writer) in list(self.workers.items()):
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
        self.workers.clear()

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        raw = await recv_bytes(reader)
        if not raw:
            writer.close()
            return
        handshake = json.loads(raw.decode("utf-8"))
        worker_id = handshake.get("worker_id", "node_unknown")
        self.workers[worker_id] = (reader, writer)
        await send_bytes(writer, json.dumps({"type": "HANDSHAKE_ACK"}).encode("utf-8"))

        try:
            while not reader.at_eof():
                await asyncio.sleep(0.1)
        except Exception:
            pass
        finally:
            self.workers.pop(worker_id, None)
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def wait_for_workers(self, min_workers: int = 2, timeout: float = 10.0):
        start = time.time()
        while len(self.workers) < min_workers:
            if time.time() - start > timeout:
                raise TimeoutError(f"Expected {min_workers} workers, got {len(self.workers)}")
            await asyncio.sleep(0.05)

    async def dispatch_job(self, dataset: np.ndarray, scale: float = 2.0) -> Tuple[bool, str, Optional[np.ndarray], Optional[MerkleTree]]:
        worker_ids = list(self.workers.keys())
        if not worker_ids:
            return False, "No workers connected", None, None

        chunks = np.array_split(dataset, len(worker_ids))
        tasks = []

        for task_id, (w_id, chunk) in enumerate(zip(worker_ids, chunks)):
            reader, writer = self.workers[w_id]
            tasks.append(self._dispatch_to_worker(w_id, reader, writer, task_id, chunk, scale))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed_chunks = []
        leaf_hashes = []

        for res in results:
            if isinstance(res, Exception) or not res or not res.get("success"):
                return False, f"Worker failure: {res}", None, None
            
            arr = res["result"]
            computed_hash = hash_array_block(arr)
            
            # Cryptographic block integrity audit
            if computed_hash != res["block_hash"]:
                return False, f"Tamper alert on node {res['worker_id']}: hash mismatch", None, None

            processed_chunks.append(arr)
            leaf_hashes.append(res["block_hash"])

        final_array = np.concatenate(processed_chunks)
        tree = MerkleTree(leaf_hashes)
        return True, "Consensus verified", final_array, tree

    async def _dispatch_to_worker(self, worker_id: str, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, task_id: int, chunk: np.ndarray, scale: float):
        meta = json.dumps({"task_id": task_id, "scale": scale, "length": len(chunk)}).encode("utf-8")
        payload = struct.pack("!I", len(meta)) + meta + chunk.tobytes()
        await send_bytes(writer, payload)

        res_raw = await recv_bytes(reader)
        if not res_raw:
            return {"success": False}

        meta_len = struct.unpack("!I", res_raw[:4])[0]
        meta_json = json.loads(res_raw[4:4+meta_len].decode("utf-8"))
        result_arr = np.frombuffer(res_raw[4+meta_len:], dtype=np.float64)

        return {
            "success": True,
            "worker_id": worker_id,
            "task_id": meta_json["task_id"],
            "block_hash": meta_json["block_hash"],
            "result": result_arr
        }

async def run_worker_node(host: str = "127.0.0.1", port: int = 8765, worker_id: str = "node_01", simulate_tamper: bool = False, ssl_context: Optional[ssl.SSLContext] = None):
    try:
        reader, writer = await asyncio.open_connection(host, port, ssl=ssl_context)
        await send_bytes(writer, json.dumps({"type": "HANDSHAKE", "worker_id": worker_id}).encode("utf-8"))
        ack = await recv_bytes(reader)
        if not ack:
            writer.close()
            await writer.wait_closed()
            return

        while True:
            msg = await recv_bytes(reader)
            if not msg:
                break

            meta_len = struct.unpack("!I", msg[:4])[0]
            meta = json.loads(msg[4:4+meta_len].decode("utf-8"))
            arr = np.frombuffer(msg[4+meta_len:], dtype=np.float64).copy()

            result = arr * meta.get("scale", 1.0)
            
            # Compute legitimate hash first
            block_hash = hash_array_block(result)

            # If simulating a tampered node, corrupt the array data without updating the hash signature
            if simulate_tamper:
                result[0] += 9999.0

            res_meta = json.dumps({"task_id": meta["task_id"], "block_hash": block_hash}).encode("utf-8")
            res_payload = struct.pack("!I", len(res_meta)) + res_meta + result.tobytes()
            await send_bytes(writer, res_payload)

        writer.close()
        await writer.wait_closed()
    except asyncio.CancelledError:
        pass
    except Exception:
        pass
