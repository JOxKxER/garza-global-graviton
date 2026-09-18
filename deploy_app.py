import os

app_code = '''from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
import os, shutil, subprocess, json

app = FastAPI(title="Data Mesh Vault & Quant Swarm")

@app.get("/", response_class=HTMLResponse)
def dashboard():
    i_cnt = len(os.listdir("data_inbox")) if os.path.exists("data_inbox") else 0
    assets = os.listdir("assets_out") if os.path.exists("assets_out") else []
    asset_list = "".join([f"<li>{a}</li>" for a in assets]) or "<li>No processed assets yet.</li>"
    
    ledger_items = []
    if os.path.exists("swarm_intelligence_ledger.json"):
        try:
            with open("swarm_intelligence_ledger.json", "r", encoding="utf-8") as ledger_file:
                ledger_items = json.load(ledger_file)
        except Exception:
            ledger_items = []
            
    pattern_html = "".join([f"<li><b>{p[\"source_id\"]}</b>: {p[\"direction\"]} {p[\"asset\"]} (Confidence: {p[\"confidence\"]}) - <i>{p[\"rationale\"]}</i></li>" for p in ledger_items[-5:]]) or "<li>No high-signal patterns tracked yet.</li>"
    
    html = f\"\"\"<!DOCTYPE html><html><head><title>Data Mesh Vault & Quant Swarm</title><style>body{{font-family:sans-serif;background:#0f172a;color:#f8fafc;padding:40px;}}.card{{background:#1e293b;padding:20px;border-radius:8px;margin-bottom:20px;}}ul{{color:#38bdf8;padding-left:20px;}}button{{background:#0284c7;color:white;border:none;padding:10px 20px;border-radius:6px;font-weight:bold;cursor:pointer;}}button:hover{{background:#0ea5e9;}}</style></head><body><div style='max-width:700px;margin:auto'><h1>Data Mesh Vault & Quant Swarm</h1><div class='card'><h3>Inbox Count: {i_cnt}</h3></div><div class='card'><h3>Tracked Intelligence Ledger</h3><ul>{pattern_html}</ul></div><div class='card'><h3>Processed Assets</h3><ul>{asset_list}</ul></div><div class='card'><h3>Upload File</h3><form action='/upload' method='post' enctype='multipart/form-data'><input type='file' name='file'><br><br><button type='submit'>Upload</button></form></div><div class='card'><h3>Autonomous Quant Swarm</h3><form action='/run_swarm' method='post'><button type='submit'>Execute Paper Swarm Simulation</button></form></div></div></body></html>\"\"\"
    return html

@app.post("/upload")
def upload(file: UploadFile = File(...)):
    os.makedirs("data_inbox", exist_ok=True)
    filename = os.path.basename(file.filename)
    with open(os.path.join("data_inbox", filename), "wb") as b:
        shutil.copyfileobj(file.file, b)
    return RedirectResponse(url="/", status_code=303)

@app.post("/run_swarm")
def run_swarm():
    subprocess.Popen(["python", "run_adaptive_swarm_demo.py"])
    return RedirectResponse(url="/", status_code=303)
'''

os.makedirs("web_dashboard", exist_ok=True)
with open("web_dashboard/app.py", "w", encoding="utf-8") as f:
    f.write(app_code)
print("Dashboard app.py successfully compiled and deployed!")
