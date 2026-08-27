import asyncio

import numpy as np

from src.fractal_processor import FractalSignalProcessor
from src.main import create_app
from src.merkle_verifier import StateIntegrityChain
from src.telemetry_worker import BackgroundTelemetryWorker, TelemetryPacket
from src.toroidal_router import ToroidalMeshRouter


def test_toroidal_router_wraps_edges():
    router = ToroidalMeshRouter(width=16, height=16)
    route = router.route((15, 15), (0, 0))
    assert round(route.distance, 6) == round(2**0.5, 6)


def test_fractal_processor_returns_live_metrics():
    result = FractalSignalProcessor().analyze("aabbcc", depth=2)
    assert result["status"] == "success"
    assert result["signal_length"] == 6
    assert result["fractal_depth"] == 2


def test_state_integrity_chain_detects_tampering():
    chain = StateIntegrityChain()
    chain.append({"frame": 1, "value": 10})
    chain.append({"frame": 2, "value": 20})
    assert chain.verify()[0] is True
    chain.entries[1]["state"]["value"] = 999
    assert chain.verify()[0] is False


def test_background_worker_processes_packet():
    async def run_test():
        worker = BackgroundTelemetryWorker()
        packet = TelemetryPacket(
            "frame-1",
            np.array([[1.0, 0.0, 0.0, 0.0]]),
            0.0,
        )
        await worker.start()
        await worker.submit(packet)
        await worker.queue.join()
        assert packet.result["status"] == "success"
        assert worker.processed_count == 1
        await worker.stop()

    asyncio.run(run_test())


def test_main_registers_final_module_routes():
    application = create_app()
    paths = {route.path for route in application.routes}
    assert "/api/v1/mesh/route" in paths
    assert "/api/v1/signals/analyze" in paths
    assert "/api/v1/telemetry/ingest" in paths
    assert "/api/v1/telemetry/status" in paths
