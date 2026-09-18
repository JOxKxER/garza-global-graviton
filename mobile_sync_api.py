from fastapi import FastAPI, HTTPException
import aiosqlite
import urllib.request
import json
import os

app = FastAPI(title="Garza Global Graviton Mobile Sync API")
DB_PATH = "V:\\03_Source_Code\\data_in\\mesh_telemetry.db"
LOCAL_LLM_URL = "http://127.0.0.1:8011/v1/chat/completions"

@app.get("/telemetry")
async def get_telemetry():
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=404, detail="Database not initialized.")
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT node_id, timestamp, metric_key, metric_value FROM node_telemetry") as cursor:
            rows = await cursor.fetchall()
            return [{"node_id": r[0], "timestamp": r[1], "metric_key": r[2], "metric_value": r[3]} for r in rows]

@app.post("/query-joker")
async def query_joker(payload: dict):
    prompt = payload.get("prompt", "Status check")
    req_payload = {
        "model": "Qwen",
        "messages": [
            {"role": "system", "content": "You are Joker, a specialized local AI business partner and coding assistant built for Joel Garza's workspace."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }
    data = json.dumps(req_payload).encode("utf-8")
    req = urllib.request.Request(LOCAL_LLM_URL, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))
            return {"response": result["choices"][0]["message"]["content"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)