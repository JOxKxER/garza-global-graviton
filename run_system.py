"""
run_system.py - Master orchestrator: boots feed_generator.py,
advanced_pipeline.py, and syndication_worker.py together as a single
end-to-end autonomous asset pipeline, with unified graceful shutdown.

Usage:
    python run_system.py

Ctrl+C (or a SIGTERM from a process manager) stops all three children
gracefully -- each one drains its current work item and exits cleanly
rather than being hard-killed mid-write.
"""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
PYTHON_EXE = sys.executable

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(REPO_ROOT / "run_system.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("run_system")

# Same environment hardening lessons as machine_boost_supervisor.py: force
# UTF-8 so children that print non-ASCII output don't crash without a real
# console, and force unbuffered output so their logs stream promptly instead
# of sitting in a block-buffered pipe.
_CHILD_ENV = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1", PYTHONUNBUFFERED="1")

# (script, restart-on-unexpected-exit)
MANAGED_SCRIPTS = [
    "feed_generator.py",
    "advanced_pipeline.py",
    "syndication_worker.py",
]

_IS_WINDOWS = os.name == "nt"


class ManagedProcess:
    def __init__(self, script_name: str):
        self.script_name = script_name
        self.process: subprocess.Popen | None = None
        self._stop_requested = threading.Event()
        self._reader_thread: threading.Thread | None = None

    def start(self) -> None:
        popen_kwargs = dict(
            cwd=str(REPO_ROOT),
            env=_CHILD_ENV,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if _IS_WINDOWS:
            # New process group so we can deliver CTRL_BREAK_EVENT to just
            # this child later, instead of it going to our own console group.
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

        self.process = subprocess.Popen([PYTHON_EXE, self.script_name], **popen_kwargs)
        self._reader_thread = threading.Thread(target=self._pump_output, daemon=True)
        self._reader_thread.start()
        log.info("Started %s (pid=%s)", self.script_name, self.process.pid)

    def _pump_output(self) -> None:
        assert self.process is not None and self.process.stdout is not None
        for line in self.process.stdout:
            log.info("[%s] %s", self.script_name, line.rstrip())

    def is_alive(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def request_stop(self) -> None:
        self._stop_requested.set()
        if not self.process or not self.is_alive():
            return
        try:
            if _IS_WINDOWS:
                # Graceful: fires SIGBREAK in the child, which its own
                # signal handler catches to exit its loop cleanly.
                self.process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                self.process.send_signal(signal.SIGTERM)
        except (ProcessLookupError, OSError) as exc:
            log.warning("Could not signal %s gracefully: %s", self.script_name, exc)

    def wait_or_kill(self, timeout_seconds: float) -> None:
        if not self.process:
            return
        try:
            self.process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            log.warning("%s did not exit within %ss; forcing kill.", self.script_name, timeout_seconds)
            self.process.kill()
            self.process.wait(timeout=10)

    @property
    def stop_was_requested(self) -> bool:
        return self._stop_requested.is_set()


class SystemOrchestrator:
    def __init__(self, scripts: list[str], restart_backoff_seconds: float = 5.0):
        self.scripts = scripts
        self.restart_backoff_seconds = restart_backoff_seconds
        self._shutdown = threading.Event()
        self._managed: dict[str, ManagedProcess] = {}

        signal.signal(signal.SIGINT, self._handle_exit)
        signal.signal(signal.SIGTERM, self._handle_exit)

    def _handle_exit(self, signum, frame) -> None:
        log.info("Orchestrator received shutdown signal; stopping all managed processes...")
        print("\n[run_system] Graceful shutdown initiated for the whole pipeline...")
        self._shutdown.set()

    def _supervise_one(self, script_name: str) -> None:
        managed = ManagedProcess(script_name)
        self._managed[script_name] = managed
        managed.start()

        while not self._shutdown.is_set():
            if not managed.is_alive():
                if managed.stop_was_requested:
                    break
                log.warning(
                    "%s exited unexpectedly; restarting in %ss.", script_name, self.restart_backoff_seconds
                )
                time.sleep(self.restart_backoff_seconds)
                if self._shutdown.is_set():
                    break
                managed.start()
            time.sleep(1)

        managed.request_stop()
        managed.wait_or_kill(timeout_seconds=15)
        log.info("%s fully stopped.", script_name)

    def run(self) -> None:
        log.info("=== run_system starting: %s ===", ", ".join(self.scripts))
        threads = [
            threading.Thread(target=self._supervise_one, args=(script,), daemon=True)
            for script in self.scripts
        ]
        for t in threads:
            t.start()

        try:
            while not self._shutdown.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            self._shutdown.set()

        for t in threads:
            t.join(timeout=30)
        log.info("=== run_system: all managed processes stopped ===")
        print("[run_system] Full pipeline shutdown complete.")


if __name__ == "__main__":
    missing = [s for s in MANAGED_SCRIPTS if not (REPO_ROOT / s).is_file()]
    if missing:
        print(f"error: missing required script(s): {missing}", file=sys.stderr)
        raise SystemExit(2)

    orchestrator = SystemOrchestrator(MANAGED_SCRIPTS)
    orchestrator.run()
