import pytest
import asyncio
import numpy as np
from src.worker import AsyncNetworkCoordinator, run_worker_node

@pytest.mark.asyncio
async def test_async_tcp_network_pipeline():
    port = 8911
    coordinator = AsyncNetworkCoordinator(host="127.0.0.1", port=port)
    await coordinator.start_server()

    w1 = asyncio.create_task(run_worker_node(host="127.0.0.1", port=port, worker_id="node_good_1"))
    w2 = asyncio.create_task(run_worker_node(host="127.0.0.1", port=port, worker_id="node_good_2"))

    try:
        await coordinator.wait_for_workers(min_workers=2, timeout=5.0)
        data = np.linspace(1.0, 100.0, 1000, dtype=np.float64)
        success, msg, result, tree = await coordinator.dispatch_job(data, scale=2.0)

        assert success is True
        assert len(result) == 1000
        assert tree is not None
        assert len(tree.root_hash) == 64
    finally:
        w1.cancel()
        w2.cancel()
        await coordinator.stop_server()
        await asyncio.gather(w1, w2, return_exceptions=True)

@pytest.mark.asyncio
async def test_async_tcp_network_tamper_detection():
    port = 8912
    coordinator = AsyncNetworkCoordinator(host="127.0.0.1", port=port)
    await coordinator.start_server()

    w1 = asyncio.create_task(run_worker_node(host="127.0.0.1", port=port, worker_id="node_good", simulate_tamper=False))
    w2 = asyncio.create_task(run_worker_node(host="127.0.0.1", port=port, worker_id="node_tampered", simulate_tamper=True))

    try:
        await coordinator.wait_for_workers(min_workers=2, timeout=5.0)
        data = np.linspace(1.0, 50.0, 500, dtype=np.float64)
        success, msg, result, tree = await coordinator.dispatch_job(data, scale=1.5)

        assert success is False
        assert "Tamper alert" in msg
    finally:
        w1.cancel()
        w2.cancel()
        await coordinator.stop_server()
        await asyncio.gather(w1, w2, return_exceptions=True)
