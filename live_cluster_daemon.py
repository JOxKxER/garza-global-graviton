import asyncio
import uvicorn
import time
import random
import httpx
import os
import sys
from threading import Thread
from datetime import datetime
from pathlib import Path

def start_backend():
    """Runs the FastAPI commercial coordinator on port 8000"""
    uvicorn.run("src.api:app", host="0.0.0.0", port=8000, log_level="warning")

def continuous_traffic_worker():
    """Generates synthetic enterprise consensus workloads continuously"""
    time.sleep(3) # Wait for uvicorn warm-up
    url = "http://127.0.0.1:8000/api/v1/orders/submit"
    key = "ggg_live_secret_key_8899"
    clients = [
        "Lockheed_Aero_Div",
        "DARPA_Edge_Intake",
        "Raytheon_EW_Telemetry",
        "GeneralDynamics_Mesh",
        "Northrop_Sensor_Stream"
    ]
    
    with httpx.Client() as client:
        while True:
            client_ref = random.choice(clients)
            count = random.randint(180000, 850000)
            scale = round(random.uniform(1.5, 3.5), 2)
            try:
                client.post(
                    url,
                    headers={"x-api-key": key, "Content-Type": "application/json"},
                    json={"client_ref": client_ref, "element_count": count, "scale_factor": scale},
                    timeout=5.0
                )
            except Exception:
                pass
            time.sleep(random.uniform(2.5, 4.5))

def automated_audit_archiver():
    """Generates an audit snapshot to audit_snapshots/ every 60 seconds"""
    archive_dir = Path("audit_snapshots")
    archive_dir.mkdir(exist_ok=True)
    
    while True:
        time.sleep(60)
        try:
            with httpx.Client() as client:
                res = client.get("http://127.0.0.1:8000/api/v1/ledger/export?format=json")
                if res.status_code == 200:
                    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                    with open(archive_dir / f"audit_ledger_{ts}.json", "w", encoding="utf-8") as f:
                        f.write(res.text)
        except Exception:
            pass

if __name__ == "__main__":
    print("==========================================================")
    print("  GARZA GLOBAL GRAVITON - MASTER PRODUCTION DAEMON")
    print("  Ingress: http://127.0.0.1:8000 | Gateway: Active")
    print("==========================================================")
    
    # Thread 1: Ingestion API
    api_thread = Thread(target=start_backend, daemon=True)
    api_thread.start()
    
    # Thread 2: Continuous Traffic
    traffic_thread = Thread(target=continuous_traffic_worker, daemon=True)
    traffic_thread.start()
    
    # Thread 3: Autonomous Archiver
    archiver_thread = Thread(target=automated_audit_archiver, daemon=True)
    archiver_thread.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Cluster daemon stopped gracefully.")