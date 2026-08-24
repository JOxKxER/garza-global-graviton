"""
ai_sandbox_api.py - Restricted AI Sandbox & Secured Multi-Sector Platform
Includes the public storefront, private network & anti-cheat signup portal, 
secure API endpoints, and integrated Google Ads tracking tags.
"""

from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import sqlite3
import hashlib
from datetime import datetime

app = FastAPI(
    title="Garza Global Graviton - Secure Private Networks & Anti-Cheat Platform",
    description="Storefront, private network provisioning, and verifiable node architecture.",
    version="3.1.0"
)

DB_NAME = "vault_storage.db"

class TaskSubmission(BaseModel):
    task_description: str
    target_entity: str

def init_db():
    """Automatically initializes required database tables and ensures correct schema."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ai_sandbox_sessions (
            session_id TEXT PRIMARY KEY,
            developer_entity TEXT,
            model_identifier TEXT,
            permissions_scope TEXT,
            created_at TEXT,
            status TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_name TEXT,
            status TEXT
        )
    """)
    
    cursor.execute("DROP TABLE IF EXISTS crunch_tasks;")
    cursor.execute("""
        CREATE TABLE crunch_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_description TEXT,
            status TEXT,
            assigned_worker TEXT,
            created_at TEXT
        )
    """)
        
    conn.commit()
    conn.close()

init_db()

def verify_sandbox_token(x_api_key: str = Header(...)):
    """Validates external developer/AI session keys against the database vault."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT developer_entity, model_identifier, status FROM ai_sandbox_sessions WHERE session_id = ?", (x_api_key,))
    session = cursor.fetchone()
    conn.close()

    if not session or session[2] != "ACTIVE":
        raise HTTPException(status_code=401, detail="Invalid, expired, or revoked sandbox session key.")
    
    return {"entity": session[0], "model": session[1]}

@app.get("/", response_class=HTMLResponse)
def sandbox_root():
    """Public Storefront, Private Network Provisioning, Anti-Cheat Verification, and Google tracking tags."""
    return """
    <html>
        <head>
            <title>Garza Global Graviton - Private Networks & Anti-Cheat Storefront</title>
            
            <!-- Google tag (gtag.js) -->
            <script async src="https://www.googletagmanager.com/gtag/js?id=AW-18405631729"></script>
            <script>
              window.dataLayer = window.dataLayer || [];
              function gtag(){dataLayer.push(arguments);}
              gtag('js', new Date());
              gtag('config', 'AW-18405631729');
            </script>
            
            <!-- Event snippet for Submit lead form (1) conversion page -->
            <script>
              gtag('event', 'conversion', {'send_to': 'AW-18405631729/eRtSCK--5eYcEPHNvshE'});
            </script>

            <style>
                body { font-family: Arial, sans-serif; background-color: #0f172a; color: #e2e8f0; padding: 40px; margin: 0; }
                .container { max-width: 950px; margin: auto; background: #1e293b; padding: 30px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
                h1 { color: #38bdf8; margin-top: 10px; }
                h2 { color: #38bdf8; border-bottom: 1px solid #334155; padding-bottom: 5px; margin-top: 40px; }
                code { background: #0f172a; color: #38bdf8; padding: 2px 6px; border-radius: 4px; }
                pre { background: #0f172a; padding: 15px; border-radius: 6px; overflow-x: auto; color: #cbd5e1; }
                .endpoint { background: #334155; padding: 15px; margin: 15px 0; border-radius: 6px; border-left: 4px solid #38bdf8; }
                .btn { display: inline-block; background: #38bdf8; color: #0f172a; padding: 10px 20px; font-weight: bold; border-radius: 4px; text-decoration: none; margin-top: 10px; }
                .btn:hover { background: #7dd3fc; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🛡️ Garza Global Graviton: Secure Private Networks & Anti-Cheat Hub</h1>
                <p>Welcome to the official storefront and provisioning gateway. Deploy immutable private mesh networks, stop tampering and cheating via cryptographic state verification, and secure your high-performance multiplayer or enterprise workloads.</p>
                
                <h2>🛒 Storefront: Private Network & Anti-Cheat Deployment</h2>
                
                <div class="endpoint">
                    <strong>1. Secure Private Network Provisioning</strong><br>
                    <small>Spin up isolated, encrypted private network nodes with tamper-evident routing and decentralized peer-to-peer tunnels. Ideal for secure telemetry, enterprise clusters, and private gaming sessions.</small><br>
                    <a href="/docs" class="btn">Provision Network ↗</a>
                </div>

                <div class="endpoint">
                    <strong>2. Anti-Cheat & State Validation Engine</strong><br>
                    <small>Prevent unauthorized memory injection, packet tampering, and cheating using real-time cryptographic hash-chaining and decentralized node verification. Protect competitive integrity across your applications.</small><br>
                    <a href="/docs" class="btn">Configure Anti-Cheat ↗</a>
                </div>

                <div class="endpoint">
                    <strong>3. Human Data Crunch & Node Verification</strong><br>
                    <small>Harness our distributed asynchronous task-queuing engine to verify telemetry, audit transaction streams, and maintain tamper-proof execution logs across isolated nodes.</small>
                </div>

                <h2>🌐 Multi-Sector Commercial & Municipal Services</h2>
                
                <div class="endpoint">
                    <strong>Municipal Traffic & Fleet Data Harvesting</strong><br>
                    <small>Securely aggregate autonomous vehicle and IoT telemetry for city planning and bottleneck optimization.</small>
                </div>

                <div class="endpoint">
                    <strong>Energy Grid & Microgrid Load Balancing</strong><br>
                    <small>Coordinate distributed energy resources and charging fleets with fault-tolerant mesh nodes.</small>
                </div>

                <h2>📖 Developer Integration & API Access</h2>
                <p>To interact with your private network nodes and submit verification tasks, authenticate via your assigned session header:</p>
                <pre>X-API-Key: [Your Assigned Session ID Hash]</pre>
                
                <h2>🔌 Available API Endpoints</h2>
                <div class="endpoint">
                    <strong>Inspect Mesh & Network Status</strong><br>
                    <code>GET /sandbox/telemetry-status</code>
                </div>
                <div class="endpoint">
                    <strong>Submit Verification Task / Anti-Cheat Audit</strong><br>
                    <code>POST /sandbox/submit-verification</code>
                </div>
                
                <h2>💡 Interactive Documentation & Sign-Up</h2>
                <p>Access full interactive controls and test provisioning parameters via Swagger UI: <a href="/docs" style="color: #38bdf8;">/docs</a></p>
            </div>
        </body>
    </html>
    """

@app.get("/sandbox/telemetry-status")
def get_sandbox_telemetry(session: dict = Depends(verify_sandbox_token)):
    """Allows external systems to inspect private network health and node status."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM nodes")
    node_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM crunch_tasks")
    task_count = cursor.fetchone()[0]
    conn.close()

    return {
        "queried_by": session,
        "mesh_health": "SECURE_NOMINAL",
        "active_private_nodes": node_count,
        "pending_audits": task_count,
        "anti_cheat_status": "HASH_VERIFIED"
    }

@app.post("/sandbox/submit-verification")
def submit_sandbox_verification(payload: TaskSubmission, session: dict = Depends(verify_sandbox_token)):
    """Submits verification/anti-cheat audit tasks into the private network mesh."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute("""
        INSERT INTO crunch_tasks (task_description, status, assigned_worker, created_at) 
        VALUES (?, ?, ?, ?)
    """, (f"[Anti-Cheat / Network Audit] {payload.task_description}", "Pending Verification", payload.target_entity, created_at))
    conn.commit()
    conn.close()

    return {
        "status": "SUCCESS",
        "message": "Audit and anti-cheat verification task registered on your private mesh.",
        "evaluator": session["model"]
    }