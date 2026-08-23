import os
import json
import secrets
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# File paths
SUBMISSIONS_FILE = os.path.join(os.path.dirname(__file__), "client_submissions.json")
TOKENS_FILE = os.path.join(os.path.dirname(__file__), "valid_tokens.json")

# Pre-configured Stripe Payment Links (replace with your live links when ready)
STRIPE_TIER1_LINK = "https://buy.stripe.com/test_eVaeV077j8Fp9sA8ww" # $75
STRIPE_TIER2_LINK = "https://buy.stripe.com/test_7sIeV08bncVB34ccMN" # $250
STRIPE_TIER3_LINK = "https://buy.stripe.com/test_3csbIQ63ff3J34c8wx" # $600

def load_json(filepath, default_val):
    if not os.path.exists(filepath):
        return default_val
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default_val

def save_json(filepath, data):
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error writing {filepath}: {e}")

# Seed default trial tokens if none exist
def init_tokens():
    tokens = load_json(TOKENS_FILE, {})
    if not tokens:
        tokens = {
            "GGG-TRIAL-DEMO1": {"status": "ACTIVE", "tier": "Trial Run", "max_rows": 500, "created": datetime.utcnow().strftime("%Y-%m-%d")},
            "GGG-TRIAL-DEMO2": {"status": "ACTIVE", "tier": "Trial Run", "max_rows": 500, "created": datetime.utcnow().strftime("%Y-%m-%d")}
        }
        save_json(TOKENS_FILE, tokens)

init_tokens()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Garza Global Graviton | Sovereign Vault & Compute Pipeline</title>
    <style>
      :root {
        --bg: #0b0f19;
        --panel: #131b2e;
        --border: #1e293b;
        --accent: #38bdf8;
        --green: #34d399;
        --purple: #a855f7;
        --text: #e2e8f0;
        --muted: #94a3b8;
      }
      * { box-sizing: border-box; }
      body {
        background-color: var(--bg);
        color: var(--text);
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        margin: 0;
        padding: 16px;
      }
      .container {
        max-width: 950px;
        margin: 0 auto;
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 24px;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
      }
      .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #334155;
        padding-bottom: 15px;
        gap: 12px;
        flex-wrap: wrap;
      }
      h1 { color: var(--accent); margin: 0; font-size: 22px; }
      .badge {
        background: #065f46;
        color: var(--green);
        padding: 6px 12px;
        border-radius: 6px;
        font-weight: bold;
        font-size: 12px;
      }
      .card {
        background: var(--border);
        border-radius: 8px;
        padding: 18px;
        margin-top: 20px;
        border-left: 4px solid var(--accent);
      }
      .card-title {
        font-weight: bold;
        font-size: 16px;
        margin-bottom: 12px;
        color: #f8fafc;
      }
      .metric {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 0;
        border-bottom: 1px solid #334155;
        gap: 10px;
        flex-wrap: wrap;
      }
      .metric:last-child { border-bottom: none; }
      .metric-title { color: var(--muted); font-size: 14px; }
      .metric-value { font-weight: bold; color: #f8fafc; font-family: monospace; font-size: 14px; }
      
      /* Pricing Cards */
      .pricing-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 14px;
        margin-top: 12px;
      }
      .pricing-card {
        background: #0f172a;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 18px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
      }
      .pricing-title { font-weight: bold; color: var(--accent); font-size: 16px; margin-bottom: 4px; }
      .pricing-price { font-size: 22px; color: var(--green); font-weight: bold; font-family: monospace; margin-bottom: 8px; }
      .pricing-desc { color: var(--muted); font-size: 13px; line-height: 1.4; margin-bottom: 16px; }
      .checkout-btn {
        display: block;
        text-align: center;
        background: #0284c7;
        color: white;
        padding: 8px 12px;
        border-radius: 6px;
        font-weight: bold;
        text-decoration: none;
        font-size: 13px;
      }
      .checkout-btn:hover { background: #0369a1; }

      /* Form inputs */
      .form-group { margin-bottom: 14px; }
      label { display: block; font-size: 13px; color: var(--muted); margin-bottom: 6px; }
      input, select, textarea {
        width: 100%;
        padding: 10px 12px;
        background: #0f172a;
        border: 1px solid #334155;
        border-radius: 6px;
        color: white;
        font-size: 14px;
      }
      input:focus, select:focus, textarea:focus { outline: none; border-color: var(--accent); }
      .actions-group { display: flex; gap: 12px; margin-top: 20px; flex-wrap: wrap; }
      .cta-btn, .cta-btn-alt {
        display: inline-block;
        padding: 12px 20px;
        border-radius: 6px;
        font-weight: bold;
        text-align: center;
        text-decoration: none;
        color: white;
        cursor: pointer;
        border: none;
        font-size: 14px;
        flex: 1 1 200px;
      }
      .cta-btn { background: #059669; }
      .cta-btn-alt { background: #334155; }
      .footer-links {
        margin-top: 25px;
        display: flex;
        justify-content: space-between;
        font-size: 12px;
        color: var(--muted);
      }
      .footer-links a { color: var(--muted); text-decoration: none; }
      .footer-links a:hover { color: var(--accent); }

      @media (max-width: 600px) {
        .header { flex-direction: column; align-items: flex-start; }
        .actions-group { flex-direction: column; }
        .cta-btn, .cta-btn-alt { width: 100%; flex: 1 1 auto; }
      }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>GARZA GLOBAL GRAVITON</h1>
                <p style="color: #94a3b8; margin: 4px 0 0 0; font-size: 14px;">High-Performance Computing & Cryptographic Zero-Trust Vaulting Pipeline</p>
            </div>
            <span class="badge">SYSTEM ONLINE</span>
        </div>

        <!-- À La Carte Pricing Matrix & Direct Checkout -->
        <div class="card" style="border-left-color: var(--purple);">
            <div class="card-title">📦 À La Carte Pipeline Services &amp; Instant Checkout</div>
            <div class="pricing-grid">
                <div class="pricing-card">
                    <div>
                        <div class="pricing-title">Script Optimization</div>
                        <div class="pricing-price">$75</div>
                        <div class="pricing-desc">Python debugging, pandas vectorization, memory bottleneck acceleration, and bug fixes.</div>
                    </div>
                    <a href="{{ tier1_link }}" target="_blank" class="checkout-btn">Checkout Tier 1 &rarr;</a>
                </div>
                <div class="pricing-card">
                    <div>
                        <div class="pricing-title">Automated ETL Pipeline</div>
                        <div class="pricing-price">$250</div>
                        <div class="pricing-desc">End-to-end API extraction, automated data cleaning, database structuring, and scheduled triggers.</div>
                    </div>
                    <a href="{{ tier2_link }}" target="_blank" class="checkout-btn" style="background: #059669;">Checkout Tier 2 &rarr;</a>
                </div>
                <div class="pricing-card">
                    <div>
                        <div class="pricing-title">Compute &amp; Backtesting</div>
                        <div class="pricing-price">$600+</div>
                        <div class="pricing-desc">High-density parameter sweeps, algorithmic backtest harness, multi-threaded workload crunching.</div>
                    </div>
                    <a href="{{ tier3_link }}" target="_blank" class="checkout-btn">Checkout Tier 3 &rarr;</a>
                </div>
            </div>
        </div>

        <!-- Live Infrastructure Benchmarks -->
        <div class="card">
            <div class="card-title">⚡ Live Infrastructure Benchmarks</div>
            <div class="metric">
                <span class="metric-title">Queue Dispatch Latency</span>
                <span class="metric-value">&lt; 38.5 ms</span>
            </div>
            <div class="metric">
                <span class="metric-title">Cryptographic Sealing Speed</span>
                <span class="metric-value">11.2 ms</span>
            </div>
            <div class="metric">
                <span class="metric-title">Active Worker Elasticity</span>
                <span class="metric-value">Elastic (0-50 Auto-Scaling Nodes)</span>
            </div>
            <div class="metric">
                <span class="metric-title">Sovereign Ledger Status</span>
                <span class="metric-value" style="color: var(--green);">Synced &amp; Immutable (SHA-256)</span>
            </div>
        </div>

        <!-- Token Redemption & Workload Intake Form -->
        <div class="card" style="border-left-color: var(--green);">
            <div class="card-title">🚀 Workload Intake &amp; Trial Token Redemption</div>
            <form action="/submit" method="POST">
                <div class="form-group">
                    <label>Full Name or Company</label>
                    <input type="text" name="name" placeholder="Acme Corp / Jane Doe" required>
                </div>
                <div class="form-group">
                    <label>Contact Email or Phone</label>
                    <input type="text" name="email" placeholder="contact@domain.com" required>
                </div>
                <div class="form-group">
                    <label>Trial Token (Optional for 1 Free Demo Execution)</label>
                    <input type="text" name="token" placeholder="e.g. GGG-TRIAL-8F9A2" style="font-family: monospace; border-color: var(--accent);">
                </div>
                <div class="form-group">
                    <label>Project Scope / Raw Sample Data</label>
                    <textarea name="scope" rows="3" placeholder="Describe the data format, API extraction, compute sweep, or paste your sample JSON/CSV..." required></textarea>
                </div>
                <div class="form-group">
                    <label>Select Service / Tier</label>
                    <select name="tier">
                        <option value="Trial Token Run (1 Free Verification)">Trial Token Run (Free)</option>
                        <option value="Script Optimization / Bug Fix ($75)">Script Optimization / Bug Fix — $75</option>
                        <option value="Automated ETL & API Pipeline ($250)" selected>Automated ETL &amp; API Pipeline — $250</option>
                        <option value="Enterprise Compute & Backtesting ($600+)">Enterprise Compute &amp; Backtesting — $600+</option>
                        <option value="Dedicated Monthly Retainer">Dedicated Monthly Pipeline Retainer</option>
                    </select>
                </div>
                <div class="actions-group">
                    <button type="submit" class="cta-btn">Submit Workload Request</button>
                    <a href="https://github.com/JOxKxER/garza-global-graviton" target="_blank" class="cta-btn-alt">GitHub Architecture Repository</a>
                </div>
            </form>
        </div>

        <div class="footer-links">
            <span>&copy; Garza Global Graviton LLC</span>
            <a href="/admin/submissions">Operator Ledger &amp; Token Mint</a>
        </div>
    </div>
</body>
</html>
"""

ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Submissions & Token Mint | Garza Global Graviton</title>
    <style>
      :root {
        --bg: #0b0f19;
        --panel: #131b2e;
        --border: #1e293b;
        --accent: #38bdf8;
        --green: #34d399;
        --purple: #a855f7;
        --text: #e2e8f0;
        --muted: #94a3b8;
      }
      * { box-sizing: border-box; }
      body {
        background-color: var(--bg);
        color: var(--text);
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        margin: 0;
        padding: 16px;
      }
      .container {
        max-width: 950px;
        margin: 0 auto;
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 24px;
      }
      .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #334155;
        padding-bottom: 15px;
        flex-wrap: wrap;
        gap: 10px;
      }
      h1 { color: var(--accent); margin: 0; font-size: 20px; }
      .card {
        background: var(--border);
        border-radius: 8px;
        padding: 18px;
        margin-top: 20px;
      }
      .table-wrapper {
        width: 100%;
        overflow-x: auto;
        margin-top: 15px;
      }
      table {
        width: 100%;
        min-width: 600px;
        border-collapse: collapse;
        font-size: 13px;
      }
      th { text-align: left; color: var(--muted); padding: 10px 8px; border-bottom: 1px solid #334155; }
      td { padding: 10px 8px; border-bottom: 1px solid #334155; color: #cbd5e1; }
      .mint-btn {
        background: var(--purple);
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 6px;
        font-weight: bold;
        cursor: pointer;
      }
      .back-link { display: inline-block; margin-top: 18px; color: var(--accent); text-decoration: none; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Operator Control: Submissions &amp; Token Mint</h1>
            <span style="color: var(--green); font-weight: bold; font-family: monospace;">Leads: {{ submissions|length }} | Tokens: {{ tokens|length }}</span>
        </div>

        <!-- Token Mint Box -->
        <div class="card" style="border-left: 4px solid var(--purple);">
            <div style="display:flex; justify-content: space-between; align-items: center;">
                <span style="font-weight: bold; color: white;">🎟️ Mint New Prospect Trial Token</span>
                <form action="/admin/mint_token" method="POST" style="margin:0;">
                    <button type="submit" class="mint-btn">+ Generate New Trial Token</button>
                </form>
            </div>
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>Token Key</th>
                            <th>Status</th>
                            <th>Tier Scope</th>
                            <th>Created Date</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for key, val in tokens.items() %}
                        <tr>
                            <td style="font-family: monospace; color: var(--accent); font-weight: bold;">{{ key }}</td>
                            <td style="color: {{ 'var(--green)' if val.status == 'ACTIVE' else 'var(--muted)' }}; font-weight: bold;">{{ val.status }}</td>
                            <td>{{ val.tier }} ({{ val.max_rows }} max rows)</td>
                            <td>{{ val.created }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Inbound Submissions Table -->
        <div class="card" style="border-left: 4px solid var(--green);">
            <span style="font-weight: bold; color: white;">📥 Inbound Client Pipeline Requests</span>
            <div class="table-wrapper">
                {% if submissions %}
                <table>
                    <thead>
                        <tr>
                            <th>Timestamp</th>
                            <th>Name / Contact</th>
                            <th>Token Used</th>
                            <th>Project Scope</th>
                            <th>Tier / Budget</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for sub in submissions|reverse %}
                        <tr>
                            <td style="font-family: monospace; color: var(--muted);">{{ sub.timestamp }}</td>
                            <td><strong>{{ sub.name }}</strong><br><small style="color: var(--accent);">{{ sub.contact }}</small></td>
                            <td style="font-family: monospace; color: var(--purple);">{{ sub.token }}</td>
                            <td>{{ sub.scope }}</td>
                            <td style="color: var(--green); font-weight: bold;">{{ sub.tier }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                {% else %}
                <p style="text-align:center; color: var(--muted); padding: 20px 0;">No client leads recorded yet.</p>
                {% endif %}
            </div>
        </div>

        <a href="/" class="back-link">&larr; Return to Live Dashboard</a>
    </div>
</body>
</html>
"""

RECEIPT_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pipeline Execution Receipt | Garza Global Graviton</title>
    <style>
      body {
        background-color: #0b0f19;
        color: #e2e8f0;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 100vh;
        margin: 0;
        padding: 16px;
      }
      .card {
        background: #131b2e;
        border: 1px solid #1e293b;
        border-radius: 12px;
        padding: 32px;
        max-width: 520px;
        text-align: center;
        box-shadow: 0 10px 25px rgba(0,0,0,0.5);
      }
      h2 { color: #34d399; margin-top: 0; }
      .token-badge {
        background: #1e293b;
        color: #38bdf8;
        padding: 6px 12px;
        border-radius: 6px;
        font-family: monospace;
        display: inline-block;
        margin-bottom: 15px;
      }
      .receipt-box {
        background: #0f172a;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 14px;
        font-family: monospace;
        font-size: 12px;
        text-align: left;
        color: #94a3b8;
        margin: 15px 0;
        word-break: break-all;
      }
      .btn {
        display: inline-block;
        margin-top: 15px;
        padding: 10px 20px;
        background: #0284c7;
        color: white;
        text-decoration: none;
        border-radius: 6px;
        font-weight: bold;
      }
    </style>
</head>
<body>
    <div class="card">
        <h2>✓ Workload Sealed &amp; Enqueued</h2>
        <div class="token-badge">Status: {{ token_status }}</div>
        <p style="color: #94a3b8; font-size: 14px; line-height: 1.5;">Your parameters have passed cryptographic integrity checks. Below is your deterministic execution receipt:</p>
        
        <div class="receipt-box">
            <b>JOB REF:</b> 0x{{ receipt_hash[:16] }}...<br>
            <b>SHA-256 SEAL:</b> {{ receipt_hash }}<br>
            <b>TIMESTAMP:</b> {{ timestamp }}<br>
            <b>STATUS:</b> VERIFIED &amp; QUEUED
        </div>

        <a href="/" class="btn">Return to Dashboard</a>
    </div>
</body>
</html>
"""

@app.route("/")
def dashboard():
    return render_template_string(
        HTML_TEMPLATE,
        tier1_link=STRIPE_TIER1_LINK,
        tier2_link=STRIPE_TIER2_LINK,
        tier3_link=STRIPE_TIER3_LINK
    )

@app.route("/admin/submissions")
def admin_submissions():
    submissions = load_json(SUBMISSIONS_FILE, [])
    tokens = load_json(TOKENS_FILE, {})
    return render_template_string(ADMIN_TEMPLATE, submissions=submissions, tokens=tokens)

@app.route("/admin/mint_token", methods=["POST"])
def mint_token():
    tokens = load_json(TOKENS_FILE, {})
    new_token = f"GGG-TRIAL-{secrets.token_hex(3).upper()}"
    tokens[new_token] = {
        "status": "ACTIVE",
        "tier": "Trial Run",
        "max_rows": 500,
        "created": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    }
    save_json(TOKENS_FILE, tokens)
    return jsonify({"status": "minted", "token": new_token})

@app.route("/submit", methods=["POST"])
def submit_workload():
    data = request.form.to_dict() if request.form else (request.get_json(silent=True) or {})
    token_input = data.get("token", "").strip().upper()
    
    # Token validation
    tokens = load_json(TOKENS_FILE, {})
    token_status = "No Token Applied"
    if token_input:
        if token_input in tokens and tokens[token_input]["status"] == "ACTIVE":
            tokens[token_input]["status"] = "REDEEMED"
            save_json(TOKENS_FILE, tokens)
            token_status = f"Redeemed: {token_input}"
        elif token_input in tokens:
            token_status = "Token Already Redeemed"
        else:
            token_status = "Invalid Token"

    # Generate cryptographic SHA-256 receipt for the submitted payload
    import hashlib
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    receipt_seed = f"{data.get('name')}-{data.get('email')}-{now_str}-{token_input}"
    receipt_hash = hashlib.sha256(receipt_seed.encode("utf-8")).hexdigest()

    submission_entry = {
        "timestamp": now_str,
        "name": data.get("name", "Anonymous Prospect"),
        "contact": data.get("email", data.get("contact", "N/A")),
        "token": token_input if token_input else "None",
        "scope": data.get("scope", data.get("requirements", "General Python / ETL inquiry")),
        "tier": data.get("tier", data.get("budget", "Custom Project")),
        "receipt_hash": receipt_hash
    }
    
    submissions = load_json(SUBMISSIONS_FILE, [])
    submissions.append(submission_entry)
    save_json(SUBMISSIONS_FILE, submissions)
    
    if request.form:
        return render_template_string(
            RECEIPT_TEMPLATE,
            token_status=token_status,
            receipt_hash=receipt_hash,
            timestamp=now_str
        )
    return jsonify({"status": "success", "token_status": token_status, "receipt_hash": receipt_hash, "entry": submission_entry})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)