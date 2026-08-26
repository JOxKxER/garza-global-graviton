from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import datetime

app = FastAPI(title="Graviton Telemetry Ingestion Node", version="1.0")

# Enable CORS so your local HTML dashboard can communicate with it
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage buffer (Simulating a secure local database table)
telemetry_storage = []

class TelemetryPayload(BaseModel):
    lat: float
    lon: float
    alt: int
    battery: int
    timestamp: Optional[str] = None

@app.get("/")
def read_root():
    return {"status": "ONLINE", "node": "Garza Global Graviton Relay", "active_buffer_count": len(telemetry_storage)}

@app.post("/telemetry/ingest")
def ingest_telemetry(payload: TelemetryPayload):
    # Stamp timestamp if missing
    data_packet = payload.dict()
    data_packet["timestamp"] = data_packet.get("timestamp") or datetime.datetime.utcnow().isoformat()
    
    # Append to local storage buffer
    telemetry_storage.append(data_packet)
    
    print(f"[INCOMING PACKET] Lat: {payload.lat}, Lon: {payload.lon}, Battery: {payload.battery}%")
    return {"status": "SUCCESS", "stored_at_index": len(telemetry_storage) - 1}

@app.get("/telemetry/feed")
def get_telemetry_feed():
    # Return the latest captured payloads for the dashboard
    return {"total_packets": len(telemetry_storage), "data": telemetry_storage[-50:]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)