"""
machine_boost_supervisor.py - Runs this machine's legitimate maintenance/
health daemons together, on a schedule, with automatic restart for the
long-running ones. Designed to be launched directly for testing, or wrapped
by machine_boost_service.py as a Windows service that starts at boot.

Included modules (all real health/maintenance utilities in this repo):
  - watchdog_daemon.py   (system audit)          every 5 minutes
  - system_watchdog.py   (fleet health + alert)  every 5 minutes
  - snapshot_daemon.py   (verified DB backup)    every 60 minutes
  - mesh_ping_daemon.py  (peer reachability)     every 1 minute
  - health_monitor.py    (self-looping monitor)  started once, restarted if it dies

Deliberately EXCLUDED: traffic_daemon.py and live_cluster_daemon.py. Those
two do not perform any maintenance/boosting function -- they generate fake
synthetic "client orders" tagged with real defense-contractor names
(Lockheed, DARPA, Raytheon, General Dynamics, Northrop) against a local API
using a hardcoded key. Running that continuously at every machine startup
would fabricate persistent fake usage data attributed to real companies,
which is not something this script will automate. Remove them from
EXCLUDED_NOTE below only after you've confirmed that's actually intended
and the data it produces will never be presented as real customer activity.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
LOG_DIR = REPO_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "machine_boost_supervisor.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("machine_boost")

PYTHON_EXE = sys.executable

# Child scripts print emoji without forcing an encoding; under a Windows
# service (no console at all) or the default cp1252 console codepage that
# crashes them outright. Force UTF-8 on every child instead of patching each
# script individually. PYTHONUNBUFFERED matters for the persistent module:
# stdout is fully block-buffered (not line-buffered) once it's a pipe rather
# than a real console, so without this its output could sit invisible in the
# child's internal buffer indefinitely.
_CHILD_ENV = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1", PYTHONUNBUFFERED="1")

# (script name, run interval in seconds). One run per interval, sequential --
# these are lightweight audits, not meant to overlap with themselves.
INTERVAL_MODULES = [
    ("watchdog_daemon.py", 300),
    ("system_watchdog.py", 300),
    ("snapshot_daemon.py", 3600),
    ("mesh_ping_daemon.py", 60),
]

# Long-running scripts that loop internally; launched once and restarted if
# they ever exit (crash or otherwise).
PERSISTENT_MODULES = [
    "health_monitor.py",
]


def _run_once(script_name: str) -> None:
    script_path = REPO_ROOT / script_name
    if not script_path.is_file():
        log.warning("Skipping missing module: %s", script_name)
        return
    try:
        result = subprocess.run(
            [PYTHON_EXE, str(script_path)],
            cwd=str(REPO_ROOT),
            env=_CHILD_ENV,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
            check=False,
        )
        if result.stdout:
            log.info("[%s] %s", script_name, result.stdout.strip()[-2000:])
        if result.returncode != 0:
            log.warning("[%s] exited with code %s: %s", script_name, result.returncode, result.stderr[-1000:])
    except subprocess.TimeoutExpired:
        log.error("[%s] timed out after 600s", script_name)
    except Exception:
        log.exception("[%s] failed to run", script_name)


def _interval_loop(script_name: str, interval_seconds: int, stop_event: threading.Event) -> None:
    log.info("Starting interval loop for %s every %ss", script_name, interval_seconds)
    while not stop_event.is_set():
        _run_once(script_name)
        stop_event.wait(interval_seconds)
    log.info("Interval loop for %s stopped", script_name)


def _persistent_loop(script_name: str, stop_event: threading.Event) -> None:
    script_path = REPO_ROOT / script_name
    if not script_path.is_file():
        log.warning("Skipping missing persistent module: %s", script_name)
        return
    log.info("Starting persistent module %s", script_name)
    while not stop_event.is_set():
        process = subprocess.Popen(
            [PYTHON_EXE, str(script_path)],
            cwd=str(REPO_ROOT),
            env=_CHILD_ENV,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        while process.poll() is None and not stop_event.is_set():
            line = process.stdout.readline() if process.stdout else ""
            if line:
                log.info("[%s] %s", script_name, line.rstrip())
            else:
                time.sleep(0.2)
        if stop_event.is_set():
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
            break
        log.warning("[%s] exited unexpectedly (code %s); restarting in 5s", script_name, process.returncode)
        stop_event.wait(5)
    log.info("Persistent module %s stopped", script_name)


def run(stop_event: threading.Event) -> None:
    """Blocks until stop_event is set. Call from a plain script or from a
    Windows service's SvcDoRun."""
    threads = []
    for script_name, interval_seconds in INTERVAL_MODULES:
        t = threading.Thread(
            target=_interval_loop, args=(script_name, interval_seconds, stop_event), daemon=True
        )
        t.start()
        threads.append(t)
    for script_name in PERSISTENT_MODULES:
        t = threading.Thread(target=_persistent_loop, args=(script_name, stop_event), daemon=True)
        t.start()
        threads.append(t)

    log.info("machine_boost_supervisor running with %d module threads", len(threads))
    stop_event.wait()
    log.info("Stop requested; waiting for module threads to exit...")
    for t in threads:
        t.join(timeout=15)
    log.info("machine_boost_supervisor stopped")


if __name__ == "__main__":
    stop_event = threading.Event()
    try:
        run(stop_event)
    except KeyboardInterrupt:
        stop_event.set()
