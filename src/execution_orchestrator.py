"""Local execution and object-storage boundary for the Graviton suite."""

from __future__ import annotations

from concurrent.futures import Executor, ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable, Optional


@dataclass(frozen=True)
class ExecutionProfile:
    """Runtime limits selected for the current machine."""

    worker_count: int
    bucket_name: str


class ExecutionOrchestrator:
    """Draft module 20: coordinate local work and durable S3 handoff."""

    def __init__(
        self,
        profile: ExecutionProfile,
        s3_client: Any = None,
    ) -> None:
        self.profile = profile
        self.s3_client = s3_client
        self._executor: Optional[Executor] = None

    def executor(self) -> Executor:
        if self._executor is None:
            self._executor = ThreadPoolExecutor(
                max_workers=self.profile.worker_count,
                thread_name_prefix="ggg-local",
            )
        return self._executor

    def submit(self, operation: Callable[..., Any], *args: Any, **kwargs: Any):
        """Submit local work without creating unbounded threads."""
        return self.executor().submit(operation, *args, **kwargs)

    def upload_file(self, local_path: str, object_key: str) -> None:
        if self.s3_client is None:
            raise RuntimeError("S3 is not configured")
        self.s3_client.upload_file(
            local_path,
            self.profile.bucket_name,
            object_key,
        )

    def shutdown(self) -> None:
        if self._executor is not None:
            self._executor.shutdown(wait=True)
            self._executor = None
