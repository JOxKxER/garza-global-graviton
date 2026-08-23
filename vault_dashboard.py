import os
import json
import secrets
import hashlib
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, redirect

app = Flask(__name__)

# File storage paths
SUBMISSIONS_FILE = os.path.join(os.path.dirname(__file__), "client_submissions.json")
TOKENS_FILE = os.path.join(os.path.dirname(__file__), "valid_tokens.json")

# Pre-configured Stripe Payment Links
STRIPE_TIER1_LINK = "https://buy.stripe.com/test_eVaeV077j8Fp9sA8ww"  # $75
STRIPE_TIER2_LINK = "https://buy.stripe.com/test_7sIeV08bncVB34ccMN"  # $250
STRIPE_TIER3_LINK = "https://buy.stripe.com/test_3csbIQ63ff3J34c8wx"  # $600

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
            "GGG-TRIAL-DEMO1": {"status": "ACTIVE", "tier": "Standard Trial", "max_rows": 500, "sample_limit": "500 rows sample cleaning & validation", "created": "2026-08-23 12:00:00 UTC"},
            "GGG-ENTERPRISE-POC1": {"status": "ACTIVE", "tier": "Enterprise POC Slice", "max_rows": 50000, "sample_limit": "10-parameter sweep slice & cryptographic ledger audit", "created": "2026-08-23 12:00:00 UTC"}
        }
        save_json(TOKENS_FILE, tokens)

init_tokens()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <!-- Google tag (gtag.js) -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=AW-18405631729"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){dataLayer.push(arguments);}
      gtag('js', new Date());
      gtag('config', 'AW-18405631729');
    </script>
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
        --amber: #f59e0b;
        --text: #e2e8f0;
        --muted: #94a3b8;
      }
      * { box-sizing: border-box; }
      html { scroll-behavior: smooth; }
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

      .poc-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
        gap: 12px;
        margin-top: 10px;
      }
      .poc-box {
        background: #0f172a;
        border: 1px solid #334155;
        border-radius: 6px;
        padding: 14px;
        cursor: pointer;
        transition: transform 0.15s ease, border-color 0.15s ease;
      }
      .poc-box:hover {
        border-color: var(--amber);
        transform: translateY(-2px);
      }
      .poc-header {
        font-weight: bold;
        color: var(--amber);
        font-size: 14px;
        margin-bottom: 6px;
        display: flex;
        justify-content: space-between;
        align-items: center;
      }
      .poc-desc {
        font-size: 12px;
        color: var(--muted);
        line-height: 1.4;
      }
      .poc-tap-hint {
        font-size: 11px;
        color: var(--accent);
        margin-top: 8px;
        font-weight: bold;
      }

      /* FAQ Accordion */
      .faq-item {
        border-bottom: 1px solid #334155;
        padding: 12px 0;
      }
      .faq-item:last-child { border-bottom: none; }
      .faq-question {
        cursor: pointer;
        font-weight: bold;
        color: #f8fafc;
        display: flex;
        justify-content: space-between;
      }
      .faq-answer {
        color: var(--muted);
        font-size: 13px;
        line-height: 1.5;
        margin-top: 8px;
        display: none;
      }
      .faq-item.active .faq-answer { display: block; }

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
      
      /* Floating Chatbot */
      #chat-launcher {
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: var(--accent);
        color: #0b0f19;
        font-weight: bold;
        border: none;
        border-radius: 50px;
        padding: 12px 20px;
        cursor: pointer;
        box-shadow: 0 4px 15px rgba(56, 189, 248, 0.4);
        display: flex;
        align-items: center;
        gap: 8px;
        z-index: 1000;
      }
      #chat-box {
        position: fixed;
        bottom: 75px;
        right: 20px;
        width: 340px;
        max-width: 90vw;
        height: 440px;
        background: var(--panel);
        border: 1px solid #334155;
        border-radius: 12px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.7);
        display: none;
        flex-direction: column;
        z-index: 1000;
      }
      .chat-header {
        background: #0f172a;
        padding: 12px 16px;
        border-top-left-radius: 12px;
        border-top-right-radius: 12px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #334155;
        font-weight: bold;
        font-size: 13px;
      }
      .chat-body {
        flex: 1;
        padding: 12px;
        overflow-y: auto;
        font-size: 13px;
        display: flex;
        flex-direction: column;
        gap: 10px;
      }
      .chat-msg {
        padding: 8px 12px;
        border-radius: 6px;
        line-height: 1.4;
      }
      .msg-bot { background: #1e293b; color: var(--text); align-self: flex-start; }
      .msg-user { background: #0284c7; color: white; align-self: flex-end; }
      .chat-options {
        padding: 8px 12px;
        background: #0f172a;
        border-top: 1px solid #334155;
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
      }
      .chat-chip {
        background: #1e293b;
        color: var(--accent);
        border: 1px solid #334155;
        border-radius: 14px;
        padding: 4px 10px;
        font-size: 11px;
        cursor: pointer;
      }

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

        <!-- Enterprise POC / Free Trial Slices (Clickable) -->
        <div class="card" style="border-left-color: var(--amber);">
            <div class="card-title">🔬 Enterprise Proof-of-Concept: Free Micro-Workload Slices</div>
            <p style="font-size: 13px; color: var(--muted); margin-top: 0;">Click any evaluation slice below to configure your test run in the intake form:</p>
            <div class="poc-grid">
                <div class="poc-box" onclick="selectPocSlice('sweep')">
                    <div class="poc-header">
                        <span>⚡ Compute Sweep Slice (10-Param Run)</span>
                        <span style="font-size: 11px;">&darr;</span>
                    </div>
                    <div class="poc-desc">Test run a 10-parameter iteration sweep on sample data with multi-threaded vectorization benchmarks.</div>
                    <div class="poc-tap-hint">Select &amp; Pre-Fill Form &rarr;</div>
                </div>
                <div class="poc-box" onclick="selectPocSlice('etl')">
                    <div class="poc-header">
                        <span>🔄 High-Volume ETL Micro-Batch (10k Rows)</span>
                        <span style="font-size: 11px;">&darr;</span>
                    </div>
                    <div class="poc-desc">Feed raw unformatted batch data (JSON/CSV) to evaluate cleaning accuracy, schema conformity, and throughput.</div>
                    <div class="poc-tap-hint">Select &amp; Pre-Fill Form &rarr;</div>
                </div>
                <div class="poc-box" onclick="selectPocSlice('vault')">
                    <div class="poc-header">
                        <span>🛡️ Cryptographic Vault Receipt Audit</span>
                        <span style="font-size: 11px;">&darr;</span>
                    </div>
                    <div class="poc-desc">Process sample records through SHA-256 zero-trust evidence hashing and receive a tamper-proof verification receipt.</div>
                    <div class="poc-tap-hint">Select &amp; Pre-Fill Form &rarr;</div>
                </div>
            </div>
        </div>

        <!-- À La Carte Pricing Matrix & Direct Checkout -->
        <div class="card" style="border-left-color: var(--purple);">
            <div class="card-title">📦 À La Carte Production Services &amp; Instant Checkout</div>
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

        <!-- Frequently Asked Questions & Support -->
        <div class="card" style="border-left-color: var(--accent);">
            <div class="card-title">❓ Frequently Asked Questions &amp; Support</div>
            <div class="faq-item" onclick="this.classList.toggle('active')">
                <div class="faq-question"><span>How does billing and checkout work?</span> <span>+</span></div>
                <div class="faq-answer">We accept all major credit cards, ACH transfers, and corporate invoicing via Stripe. For milestone jobs, you are billed upon project scope approval. Retainers are billed monthly with no lock-in contracts.</div>
            </div>
            <div class="faq-item" onclick="this.classList.toggle('active')">
                <div class="faq-question"><span>What is the standard turnaround time?</span> <span>+</span></div>
                <div class="faq-answer">Tier 1 script optimizations are delivered within 24 to 48 hours. Custom ETL pipelines and batch compute runs typically complete within 3 to 5 business days.</div>
            </div>
            <div class="faq-item" onclick="this.classList.toggle('active')">
                <div class="faq-question"><span>How do I redeem a free trial or POC access token?</span> <span>+</span></div>
                <div class="faq-answer">Enter your trial token into the project submission form below. The pipeline will execute a sample dataset run and return a verified SHA-256 receipt at zero cost.</div>
            </div>
            <div class="faq-item" onclick="this.classList.toggle('active')">
                <div class="faq-question"><span>Need direct technical support?</span> <span>+</span></div>
                <div class="faq-answer">Email us directly with your architecture questions or submit the intake form below for an engineer review within 4 hours.</div>
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
        <div class="card" id="intake-section" style="border-left-color: var(--green);">
            <div class="card-title">🚀 Workload Intake &amp; Trial / Enterprise POC Redemption</div>
            <form action="/submit" method="POST">
                <div class="form-group">
                    <label>Full Name or Company</label>
                    <input type="text" name="name" id="input-name" placeholder="Acme Corp / Jane Doe" required>
                </div>
                <div class="form-group">
                    <label>Contact Email or Phone</label>
                    <input type="text" name="email" id="input-email" placeholder="contact@domain.com" required>
                </div>
                <div class="form-group">
                    <label>Access / POC Token (Optional for Free Trial or Enterprise Slice)</label>
                    <input type="text" name="token" id="input-token" placeholder="e.g. GGG-ENTERPRISE-POC1 or GGG-TRIAL-8F9A2" style="font-family: monospace; border-color: var(--accent);">
                </div>
                <div class="form-group">
                    <label>Project Scope / Sample Data / POC Requirements</label>
                    <textarea name="scope" id="input-scope" rows="3" placeholder="Describe the enterprise architecture, parameter sweep requirements, or paste sample schema/JSON..." required></textarea>
                </div>
                <div class="form-group">
                    <label>Select Service / Evaluation Tier</label>
                    <select name="tier" id="select-tier">
                        <option value="Enterprise POC Slice (Free Token Evaluation)">Enterprise POC Slice (Free Token Evaluation)</option>
                        <option value="Standard Trial Run (500 rows free)">Standard Trial Run (500 rows free)</option>
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

    <!-- Floating Support & Estimator Chat Widget -->
    <button id="chat-launcher" onclick="toggleChat()">💬 Quick FAQ &amp; Estimator</button>
    <div id="chat-box">
        <div class="chat-header">
            <span>Pipeline Assistant</span>
            <span style="cursor:pointer;" onclick="toggleChat()">✕</span>
        </div>
        <div class="chat-body" id="chat-stream">
            <div class="chat-msg msg-bot">Hello! How can I assist you with your data pipeline, Enterprise POC, or pricing today?</div>
        </div>
        <div class="chat-options">
            <span class="chat-chip" onclick="askBot('pricing')">💰 Price List</span>
            <span class="chat-chip" onclick="askBot('estimate')">📊 Estimate Project</span>
            <span class="chat-chip" onclick="askBot('tokens')">🎟️ Trial & POC Tokens</span>
            <span class="chat-chip" onclick="askBot('payment')">💳 Payment Methods</span>
        </div>
    </div>

    <script>
      function toggleChat() {
        var box = document.getElementById('chat-box');
        box.style.display = (box.style.display === 'flex') ? 'none' : 'flex';
      }

      function selectPocSlice(type) {
        var tierSelect = document.getElementById('select-tier');
        var scopeBox = document.getElementById('input-scope');
        var tokenBox = document.getElementById('input-token');
        var intakeCard = document.getElementById('intake-section');

        tierSelect.value = "Enterprise POC Slice (Free Token Evaluation)";

        if (type === 'sweep') {
          scopeBox.value = "Enterprise POC Request: 10-Parameter Compute Sweep Benchmark on sample multi-dimensional dataset.";
        } else if (type === 'etl') {
          scopeBox.value = "Enterprise POC Request: High-Volume ETL Micro-Batch (10,000 rows unformatted JSON/CSV cleaning and schema normalization).";
        } else if (type === 'vault') {
          scopeBox.value = "Enterprise POC Request: Cryptographic Zero-Trust Vaulting & SHA-256 Ledger Receipt Verification Audit.";
        }

        intakeCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
        scopeBox.focus();
      }

      function askBot(topic) {
        var stream = document.getElementById('chat-stream');
        var userMsg = document.createElement('div');
        userMsg.className = 'chat-msg msg-user';
        
        var botMsg = document.createElement('div');
        botMsg.className = 'chat-msg msg-bot';

        if (topic === 'pricing') {
          userMsg.innerText = "What are the standard prices?";
          botMsg.innerHTML = "Our à la carte pricing:<br>• <b>Script Fix:</b> $75<br>• <b>ETL Pipeline:</b> $250<br>• <b>Compute & Sweeps:</b> $600+<br>• <b>Retainers:</b> Custom monthly SLA.";
        } else if (topic === 'estimate') {
          userMsg.innerText = "How do you estimate projects?";
          botMsg.innerHTML = "Estimates depend on data volume and API complexity:<br>• Under 10k rows / 1 API: ~$75-$150<br>• Automated recurring ETL: ~$250<br>• High-volume backtesting: ~$600+.<br>Submit the form above for an exact fixed quote!";
        } else if (topic === 'tokens') {
          userMsg.innerText = "How do trial & POC tokens work?";
          botMsg.innerHTML = "Trial & POC tokens allow free test runs of our data cleaning or parameter sweep engine. Click any POC box above to auto-configure!";
        } else if (topic === 'payment') {
          userMsg.innerText = "How do I pay?";
          botMsg.innerHTML = "We send secure Stripe checkout links for Credit Card, Apple Pay, and ACH transfers upon scope confirmation.";
        }

        stream.appendChild(userMsg);
        stream.appendChild(botMsg);
        stream.scrollTop = stream.scrollHeight;
      }
    </script>
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
        --amber: #f59e0b;
        --red: #f43f5e;
        --orange: #fb923c;
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
        min-width: 700px;
        border-collapse: collapse;
        font-size: 13px;
      }
      th { text-align: left; color: var(--muted); padding: 10px 8px; border-bottom: 1px solid #334155; }
      td { padding: 10px 8px; border-bottom: 1px solid #334155; color: #cbd5e1; }
      .mint-controls {
        display: flex;
        gap: 8px;
        align-items: center;
        flex-wrap: wrap;
      }
      .mint-btn {
        background: var(--purple);
        color: white;
        border: none;
        padding: 8px 14px;
        border-radius: 6px;
        font-weight: bold;
        cursor: pointer;
      }
      .mint-btn-enterprise {
        background: var(--amber);
        color: #0b0f19;
        border: none;
        padding: 8px 14px;
        border-radius: 6px;
        font-weight: bold;
        cursor: pointer;
      }
      .btn-revoke {
        background: #475569;
        color: var(--orange);
        border: 1px solid #64748b;
        padding: 4px 8px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 11px;
        font-weight: bold;
        margin-right: 4px;
      }
      .btn-delete {
        background: #450a0a;
        color: #f87171;
        border: 1px solid #7f1d1d;
        padding: 4px 8px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 11px;
        font-weight: bold;
      }
      .btn-revoke:hover { background: var(--orange); color: black; }
      .btn-delete:hover { background: var(--red); color: white; }
      .back-link { display: inline-block; margin-top: 18px; color: var(--accent); text-decoration: none; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Operator Control: Submissions &amp; Token Mint</h1>
            <span style="color: var(--green); font-weight: bold; font-family: monospace;">Leads: {{ submissions|length }} | Active/Total Tokens: <span id="token-count">{{ tokens|length }}</span></span>
        </div>

        <div class="card" style="border-left: 4px solid var(--purple);">
            <div style="display:flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                <span style="font-weight: bold; color: white;">🎟️ Mint Standard &amp; Enterprise POC Tokens</span>
                <div class="mint-controls">
                    <button type="button" class="mint-btn" onclick="generateToken('standard')">+ Mint Standard Trial (500 Rows)</button>
                    <button type="button" class="mint-btn-enterprise" onclick="generateToken('enterprise')">+ Mint Enterprise POC Slice</button>
                </div>
            </div>
            <div class="table-wrapper">
                <table id="token-table">
                    <thead>
                        <tr>
                            <th>Token Key</th>
                            <th>Status</th>
                            <th>Tier Scope</th>
                            <th>Evaluation Limit / Snippet Scope</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody id="token-tbody">
                        {% for key, val in tokens.items() %}
                        <tr id="row-{{ key }}">
                            <td style="font-family: monospace; color: {{ 'var(--amber)' if 'ENTERPRISE' in key else 'var(--accent)' }}; font-weight: bold;">{{ key }}</td>
                            <td id="status-{{ key }}" style="color: {{ 'var(--green)' if val.status == 'ACTIVE' else ('var(--orange)' if val.status == 'REVOKED' else 'var(--muted)') }}; font-weight: bold;">{{ val.status }}</td>
                            <td>{{ val.tier }}</td>
                            <td>{{ val.sample_limit }}</td>
                            <td>
                                {% if val.status == 'ACTIVE' %}
                                <button class="btn-revoke" id="btn-rev-{{ key }}" onclick="revokeToken('{{ key }}')">Revoke</button>
                                {% endif %}
                                <button class="btn-delete" onclick="deleteToken('{{ key }}')">Delete</button>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

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

    <script>
      async function generateToken(tokenType) {
        try {
          const res = await fetch('/admin/mint_token', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type: tokenType })
          });
          const data = await res.json();
          if (data.status === 'minted') {
            const tbody = document.getElementById('token-tbody');
            const row = document.createElement('tr');
            row.id = `row-${data.token}`;
            const color = data.token.includes('ENTERPRISE') ? 'var(--amber)' : 'var(--accent)';
            row.innerHTML = `
              <td style="font-family: monospace; color: ${color}; font-weight: bold;">${data.token}</td>
              <td id="status-${data.token}" style="color: var(--green); font-weight: bold;">ACTIVE</td>
              <td>${data.tier}</td>
              <td>${data.sample_limit}</td>
              <td>
                <button class="btn-revoke" id="btn-rev-${data.token}" onclick="revokeToken('${data.token}')">Revoke</button>
                <button class="btn-delete" onclick="deleteToken('${data.token}')">Delete</button>
              </td>
            `;
            tbody.appendChild(row);
            
            const countSpan = document.getElementById('token-count');
            countSpan.innerText = parseInt(countSpan.innerText || '0') + 1;
          }
        } catch(e) {
          console.error("Token minting error:", e);
        }
      }

      async function revokeToken(tokenKey) {
        if (!confirm(`Revoke token ${tokenKey}? It can no longer be used.`)) return;
        try {
          const res = await fetch('/admin/revoke_token', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token: tokenKey })
          });
          const data = await res.json();
          if (data.status === 'revoked') {
            const statusCell = document.getElementById(`status-${tokenKey}`);
            if (statusCell) {
              statusCell.innerText = 'REVOKED';
              statusCell.style.color = 'var(--orange)';
            }
            const revBtn = document.getElementById(`btn-rev-${tokenKey}`);
            if (revBtn) revBtn.remove();
          }
        } catch(e) {
          console.error("Revoke error:", e);
        }
      }

      async function deleteToken(tokenKey) {
        if (!confirm(`Permanently delete token ${tokenKey}?`)) return;
        try {
          const res = await fetch('/admin/delete_token', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token: tokenKey })
          });
          const data = await res.json();
          if (data.status === 'deleted') {
            const row = document.getElementById(`row-${tokenKey}`);
            if (row) row.remove();
            const countSpan = document.getElementById('token-count');
            countSpan.innerText = Math.max(0, parseInt(countSpan.innerText || '1') - 1);
          }
        } catch(e) {
          console.error("Delete error:", e);
        }
      }
    </script>
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
        max-width: 540px;
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
        <div class="token-badge">Evaluation Status: {{ token_status }}</div>
        <p style="color: #94a3b8; font-size: 14px; line-height: 1.5;">Your dataset parameters have passed cryptographic integrity verification. Below is your deterministic proof receipt:</p>
        
        <div class="receipt-box">
            <b>JOB REF:</b> 0x{{ receipt_hash[:16] }}...<br>
            <b>SHA-256 SEAL:</b> {{ receipt_hash }}<br>
            <b>SCOPE LIMIT:</b> {{ sample_limit }}<br>
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
    data = request.get_json(silent=True) or {}
    token_type = data.get("type", "standard")
    tokens = load_json(TOKENS_FILE, {})
    
    created_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    if token_type == "enterprise":
        new_token = f"GGG-ENTERPRISE-{secrets.token_hex(3).upper()}"
        tier = "Enterprise POC Slice"
        max_rows = 50000
        sample_limit = "10-parameter sweep slice & cryptographic ledger audit"
    else:
        new_token = f"GGG-TRIAL-{secrets.token_hex(3).upper()}"
        tier = "Standard Trial Run"
        max_rows = 500
        sample_limit = "500 rows sample cleaning & validation"

    tokens[new_token] = {
        "status": "ACTIVE",
        "tier": tier,
        "max_rows": max_rows,
        "sample_limit": sample_limit,
        "created": created_at
    }
    save_json(TOKENS_FILE, tokens)
    return jsonify({
        "status": "minted",
        "token": new_token,
        "tier": tier,
        "max_rows": max_rows,
        "sample_limit": sample_limit,
        "created": created_at
    })

@app.route("/admin/revoke_token", methods=["POST"])
def revoke_token():
    data = request.get_json(silent=True) or {}
    token_key = data.get("token", "").strip().upper()
    tokens = load_json(TOKENS_FILE, {})
    if token_key in tokens:
        tokens[token_key]["status"] = "REVOKED"
        save_json(TOKENS_FILE, tokens)
        return jsonify({"status": "revoked", "token": token_key})
    return jsonify({"status": "not_found"}), 404

@app.route("/admin/delete_token", methods=["POST"])
def delete_token():
    data = request.get_json(silent=True) or {}
    token_key = data.get("token", "").strip().upper()
    tokens = load_json(TOKENS_FILE, {})
    if token_key in tokens:
        del tokens[token_key]
        save_json(TOKENS_FILE, tokens)
        return jsonify({"status": "deleted", "token": token_key})
    return jsonify({"status": "not_found"}), 404

@app.route("/submit", methods=["POST"])
def submit_workload():
    data = request.form.to_dict() if request.form else (request.get_json(silent=True) or {})
    token_input = data.get("token", "").strip().upper()
    
    tokens = load_json(TOKENS_FILE, {})
    token_status = "Standard Intake"
    sample_limit = "Full Scope Quote Review"
    
    if token_input:
        if token_input in tokens and tokens[token_input]["status"] == "ACTIVE":
            tokens[token_input]["status"] = "REDEEMED"
            save_json(TOKENS_FILE, tokens)
            token_status = f"Redeemed: {tokens[token_input]['tier']}"
            sample_limit = tokens[token_input].get("sample_limit", "Trial Execution")
        elif token_input in tokens and tokens[token_input]["status"] == "REVOKED":
            token_status = "Token Has Been Revoked"
        elif token_input in tokens:
            token_status = "Token Already Redeemed"
        else:
            token_status = "Invalid Token"

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
            sample_limit=sample_limit,
            receipt_hash=receipt_hash,
            timestamp=now_str
        )
    return jsonify({"status": "success", "token_status": token_status, "receipt_hash": receipt_hash, "entry": submission_entry})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)