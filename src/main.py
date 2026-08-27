"""Garza Global Graviton runtime bootstrap.

AWS credentials are loaded explicitly from environment variables when provided.
"""

from __future__ import annotations

import os
from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional

import numpy as np
from fastapi import FastAPI
from dotenv import load_dotenv

try:
    from .execution_orchestrator import ExecutionOrchestrator, ExecutionProfile
    from .fractal_processor import FractalSignalProcessor
    from .telemetry_worker import BackgroundTelemetryWorker, TelemetryPacket
    from .toroidal_router import ToroidalMeshRouter
except ImportError:
    from execution_orchestrator import ExecutionOrchestrator, ExecutionProfile
    from fractal_processor import FractalSignalProcessor
    from telemetry_worker import BackgroundTelemetryWorker, TelemetryPacket
    from toroidal_router import ToroidalMeshRouter


DEFAULT_BUCKET = "garza-global-graviton-storage-01"
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


def configure_local_runtime() -> int:
    """Select bounded local worker settings without overriding explicit values.
    """
    cpu_count = os.cpu_count() or 1
    worker_count = max(1, int(os.getenv("GGG_LOCAL_WORKERS", str(cpu_count))))
    os.environ.setdefault("OMP_NUM_THREADS", str(worker_count))
    os.environ.setdefault("MKL_NUM_THREADS", str(worker_count))
    os.environ.setdefault("OPENBLAS_NUM_THREADS", str(worker_count))
    os.environ.setdefault("NUMEXPR_NUM_THREADS", str(worker_count))
    return worker_count


def create_s3_client() -> Optional[Any]:
    """Create an S3 client from explicit environment credentials."""
    try:
        import boto3
    except ImportError:
        return None

    access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    if not access_key_id or not secret_access_key:
        return None

    return boto3.client(
        "s3",
        region_name=(
            os.getenv("AWS_REGION")
            or os.getenv("AWS_DEFAULT_REGION")
            or None
        ),
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
    )


def create_app() -> FastAPI:
    worker_count = configure_local_runtime()
    bucket_name = os.getenv("GGG_S3_BUCKET", DEFAULT_BUCKET)
    profile = ExecutionProfile(
        worker_count=worker_count,
        bucket_name=bucket_name,
    )
    orchestrator = ExecutionOrchestrator(profile, create_s3_client())
    router = ToroidalMeshRouter()
    fractal_processor = FractalSignalProcessor()
    telemetry_worker = BackgroundTelemetryWorker()
    application = FastAPI(title="Garza Global Graviton", version="0.2.0")
    application.state.orchestrator = orchestrator
    application.state.telemetry_worker = telemetry_worker

    @application.get("/health")
    def health() -> dict[str, Any]:
        access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        s3_configured = bool(access_key_id and secret_access_key)
        return {
            "status": "ok",
            "runtime": asdict(profile),
            "s3_configured": s3_configured,
        }

    @application.get("/api/v1/storage/status")
    def storage_status() -> dict[str, Any]:
        access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        return {
            "bucket": bucket_name,
            "configured": bool(access_key_id and secret_access_key),
        }

    @application.post("/api/v1/mesh/route")
    def mesh_route(payload: dict[str, Any]) -> dict[str, Any]:
        route = router.route(
            payload.get("source", [0, 0]),
            payload.get("target", [0, 0]),
            float(payload.get("payload_size_kb", 0.0)),
        )
        return {
            "status": "success",
            "source": route.source,
            "target": route.target,
            "distance": route.distance,
            "estimated_latency_ms": route.estimated_latency_ms,
        }

    @application.post("/api/v1/signals/analyze")
    def analyze_signal(payload: dict[str, Any]) -> dict[str, Any]:
        return fractal_processor.analyze(
            str(payload.get("signal", "")),
            int(payload.get("depth", 3)),
        )

    @application.post("/api/v1/telemetry/ingest")
    async def ingest_telemetry(payload: dict[str, Any]) -> dict[str, Any]:
        points = np.asarray(payload.get("points", []), dtype=np.float64)
        packet = TelemetryPacket(
            packet_id=str(payload.get("packet_id", "telemetry-unknown")),
            points=points,
            theta=float(payload.get("theta", 0.0)),
            plane=str(payload.get("plane", "xw")),
        )
        await telemetry_worker.start()
        await telemetry_worker.submit(packet)
        await telemetry_worker.queue.join()
        return packet.result or {
            "packet_id": packet.packet_id,
            "status": "error",
        }

    @application.get("/api/v1/telemetry/status")
    def telemetry_status() -> dict[str, Any]:
        return {
            "running": telemetry_worker.running,
            "queued": telemetry_worker.queue.qsize(),
            "processed": telemetry_worker.processed_count,
            "failed": telemetry_worker.failed_count,
        }

    return application


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=os.getenv("GGG_HOST", "127.0.0.1"),
        port=int(os.getenv("GGG_PORT", "8001")),
    )
