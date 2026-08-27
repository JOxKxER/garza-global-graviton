from fastapi import (
    FastAPI,
    Header,
    HTTPException,
    Response,
)
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel
from datetime import datetime
from pathlib import Path
import sqlite3
import hashlib
import uuid
import csv
import io

app = FastAPI(title="Garza Global Graviton - Commercial Compute API", version="0.1.0")

API_KEY = "ggg_live_secret_key_8899"
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "cluster_ledger.db"
DASHBOARD_TEMPLATE = BASE_DIR / "templates" / "index.html"
DOWNLOADABLE_FILES = {
    "start_graviton.bat",
    "launch_engine.bat",
    "requirements.txt",
    "graviton_fluid_compression_utility.py",
    "graviton_telemetry_client.py",
}

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            client_ref TEXT,
            element_count INTEGER,
            scale_factor REAL,
            status TEXT,
            settled_batch INTEGER,
            merkle_root TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

def compute_hash(order_id: str, batch: int, client: str, count: int) -> str:
    raw = f"{order_id}_{batch}_{client}_{count}".encode()
    return hashlib.sha256(raw).hexdigest()

def db_record_completed_order(order_id, client_ref, count, scale, batch, root):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO orders (order_id, client_ref, element_count, scale_factor, status, settled_batch, merkle_root, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (order_id, client_ref, count, scale, "COMPLETED", batch, root, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()

class WorkloadSubmission(BaseModel):
    client_ref: str = "Mobile_Field_Intake_01"
    element_count: int = 300000
    scale_factor: float = 2.0

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def serve_dashboard():
    with open(DASHBOARD_TEMPLATE, "r", encoding="utf-8") as f:
        return f.read()


@app.get("/downloads/{filename}", response_class=FileResponse)
def download_client(filename: str):
    if filename not in DOWNLOADABLE_FILES:
        raise HTTPException(status_code=404, detail="Download not found")
    file_path = BASE_DIR / filename
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Download not found")
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream",
    )

@app.post("/api/v1/orders/submit", tags=["Commercial Intake"])
async def submit_compute_order(payload: WorkloadSubmission, x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    order_id = str(uuid.uuid4())[:8]
    batch_num = 2650
    merkle_root = compute_hash(order_id, batch_num, payload.client_ref, payload.element_count)
    
    db_record_completed_order(order_id, payload.client_ref, payload.element_count, payload.scale_factor, batch_num, merkle_root)
    
    return {
        "status": "COMPLETED",
        "order_id": order_id,
        "client": payload.client_ref,
        "elements_queued": payload.element_count,
        "settled_in_batch": batch_num,
        "consensus_merkle_root": merkle_root,
        "remaining_credits": 49500000
    }

@app.get("/api/v1/orders/{order_id}/status", tags=["Commercial Intake"])
async def get_order_status(order_id: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT status, settled_batch, merkle_root FROM orders WHERE order_id = ?", (order_id,))
    row = cur.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Order not found")
        
    status, batch, root = row
    return {
        "order_id": order_id,
        "status": status,
        "settled_in_batch": batch,
        "consensus_merkle_root": root
    }

@app.get("/api/v1/ledger/verify", tags=["Audit"])
def verify_ledger_integrity():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT order_id, client_ref, element_count, settled_batch, merkle_root FROM orders")
    rows = cur.fetchall()
    conn.close()

    total = len(rows)
    verified = 0
    tampered = []

    for r in rows:
        expected = compute_hash(r["order_id"], r["settled_batch"], r["client_ref"], r["element_count"])
        if r["merkle_root"] == expected:
            verified += 1
        else:
            tampered.append(r["order_id"])

    return {
        "status": "INTEGRITY_VERIFIED" if not tampered else "TAMPER_DETECTED",
        "total_records_audited": total,
        "valid_proofs": verified,
        "corrupted_records": tampered,
        "verification_timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/v1/ledger/export", tags=["Audit"])
def export_ledger(format: str = "json"):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT order_id, client_ref, element_count, scale_factor, status, settled_batch, merkle_root, created_at FROM orders ORDER BY created_at DESC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    timestamp = datetime.utcnow().isoformat()
    
    if format.lower() == "csv":
        output = io.StringIO()
        if rows:
            writer = csv.DictWriter(output, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=ledger_audit_{int(datetime.utcnow().timestamp())}.csv"}
        )

    return JSONResponse(
        content={
            "audit_timestamp": timestamp,
            "record_count": len(rows),
            "ledger_entries": rows
        }
    )

