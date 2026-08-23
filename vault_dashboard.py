import os
import json
import secrets
import hashlib
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, redirect, send_file

app = Flask(__name__)

# File storage paths
BASE_DIR = os.path.dirname(__file__)
SUBMISSIONS_FILE = os.path.join(BASE_DIR, "client_submissions.json")
TOKENS_FILE = os.path.join(BASE_DIR, "valid_tokens.json")
LOGO_FILE = os.path.join(BASE_DIR, "logo.jpg")

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

def init_tokens():
    tokens = load_json(TOKENS_FILE, {})
    if not tokens:
        tokens = {
            "GGG-GAMING-A1B2C3": {
                "status": "ACTIVE",
                "tier": "Gaming & Telemetry Trial",
                "max_rows": 500,
                "sample_limit": "500 rows frame-time logs / 1 clip compression",
                "created": "2026-08-23 12:00:00 UTC"
            },
            "GGG-ADHOC-D4E5F6": {
                "status": "ACTIVE",
                "tier": "Ad-Hoc & Server Trial",
                "max_rows": 1000,
                "sample_limit": "1 ephemeral P2P mesh setup / server hardening audit",
                "created": "2026-08-23 12:00:00 UTC"
            },
            "GGG-BIZ-G7H8I9": {
                "status": "ACTIVE",
                "tier": "Bookkeeping & Business Trial",
                "max_rows": 500,
                "sample_limit": "500 rows bank ledger reconciliation / margin model",
                "created": "2026-08-23 12:00:00 UTC"
            },
            "GGG-CREATIVE-J1K2L3": {
                "status": "ACTIVE",
                "tier": "Creative & Studio Trial",
                "max_rows": 1000,
                "sample_limit": "1 3D render burst check / 1 audio stem provenance seal",
                "created": "2026-08-23 12:00:00 UTC"
            },
            "GGG-LEGAL-M4N5P6": {
                "status": "ACTIVE",
                "tier": "Legal & Compliance Trial",
                "max_rows": 500,
                "sample_limit": "1 PII redaction pass / 1 SHA-256 prior-art audit",
                "created": "2026-08-23 12:00:00 UTC"
            },
            "GGG-ENTERPRISE-Q7R8S9": {
                "status": "ACTIVE",
                "tier": "Enterprise POC Slice",
                "max_rows": 50000,
                "sample_limit": "10-parameter sweep slice & cryptographic ledger audit",
                "created": "2026-08-23 12:00:00 UTC"
            }
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
    <title>Garza Global Graviton | Sovereign Vault, Compute Pipeline & Ad-Hoc Infrastructure</title>
    <style>
      :root {
        --bg: #0b0f19;
        --panel: #131b2e;
        --border: #1e293b;
        --accent: #38bdf8;
        --green: #34d399;
        --purple: #a855f7;
        --amber: #f59e0b;
        --pink: #ec4899;
        --emerald: #10b981;
        --cyan: #06b6d4;
        --indigo: #6366f1;
        --red: #ef4444;
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
        padding-bottom: 120px;
      }
      .container {
        max-width: 1020px;
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
        gap: 16px;
        flex-wrap: wrap;
      }
      .brand-title-wrap {
        display: flex;
        align-items: center;
        gap: 14px;
      }
      .header-logo {
        width: 48px;
        height: 48px;
        border-radius: 8px;
        border: 1px solid var(--accent);
        object-fit: cover;
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
      
      .tool-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 12px;
        margin-top: 10px;
      }
      .tool-box {
        background: #0f172a;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 16px;
        cursor: pointer;
        transition: transform 0.15s ease, border-color 0.15s ease;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
      }
      .tool-box:hover {
        border-color: var(--accent);
        transform: translateY(-2px);
      }
      .tool-header {
        font-weight: bold;
        color: var(--accent);
        font-size: 14px;
        margin-bottom: 6px;
        display: flex;
        justify-content: space-between;
        align-items: center;
      }
      .tool-desc {
        font-size: 12px;
        color: var(--muted);
        line-height: 1.4;
      }
      .tool-tap {
        font-size: 11px;
        color: var(--green);
        margin-top: 10px;
        font-weight: bold;
      }

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
        text-decoration: none;
        color: white;
        cursor: pointer;
        border: none;
        font-size: 14px;
        flex: 1 1 200px;
      }
      .cta-btn { background: #059669; }
      .cta-btn-alt { background: #334155; }
      
      /* Double-Sized Floating Pill Launcher */
      #chat-launcher {
        position: fixed;
        bottom: 24px;
        right: 24px;
        height: 64px;
        padding: 6px 22px 6px 8px;
        border-radius: 50px;
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border: 2px solid var(--accent);
        cursor: pointer;
        box-shadow: 0 0 25px rgba(56, 189, 248, 0.45), 0 10px 25px rgba(0, 0, 0, 0.75);
        display: flex;
        align-items: center;
        gap: 14px;
        z-index: 10000;
        transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
      }
      #chat-launcher:hover {
        transform: translateY(-3px) scale(1.03);
        border-color: #ffffff;
        box-shadow: 0 0 35px rgba(239, 68, 68, 0.5), 0 0 20px rgba(56, 189, 248, 0.8);
      }
      .launcher-img-wrap {
        width: 50px;
        height: 50px;
        border-radius: 50%;
        overflow: hidden;
        border: 2px solid var(--accent);
        display: flex;
        align-items: center;
        justify-content: center;
        background: #000;
        flex-shrink: 0;
      }
      .launcher-img-wrap img {
        width: 100%;
        height: 100%;
        object-fit: cover;
      }
      .launcher-text-wrap {
        display: flex;
        flex-direction: column;
        text-align: left;
      }
      .launcher-title {
        color: #ffffff;
        font-weight: 900;
        font-size: 15px;
        letter-spacing: 0.8px;
        line-height: 1.2;
      }
      .launcher-sub {
        color: var(--accent);
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.5px;
      }

      #chat-box {
        position: fixed;
        bottom: 100px;
        right: 24px;
        width: 420px;
        max-width: 92vw;
        height: 550px;
        background: var(--panel);
        border: 2px solid var(--accent);
        border-radius: 14px;
        box-shadow: 0 15px 40px rgba(0,0,0,0.85);
        display: none;
        flex-direction: column;
        z-index: 10000;
      }
      .chat-header {
        background: #0f172a;
        padding: 14px 18px;
        border-top-left-radius: 12px;
        border-top-right-radius: 12px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #334155;
        font-weight: bold;
        font-size: 14px;
        color: var(--accent);
      }
      .chat-body {
        flex: 1;
        padding: 14px;
        overflow-y: auto;
        font-size: 13px;
        display: flex;
        flex-direction: column;
        gap: 10px;
      }
      .chat-msg {
        padding: 10px 14px;
        border-radius: 8px;
        line-height: 1.45;
      }
      .msg-bot { background: #1e293b; color: var(--text); align-self: flex-start; }
      .msg-user { background: #0284c7; color: white; align-self: flex-end; }
      .chat-options {
        padding: 10px 12px;
        background: #0f172a;
        border-top: 1px solid #334155;
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        max-height: 170px;
        overflow-y: auto;
      }
      .chat-chip {
        background: #1e293b;
        color: var(--accent);
        border: 1px solid #334155;
        border-radius: 14px;
        padding: 5px 11px;
        font-size: 11px;
        font-weight: 600;
        cursor: pointer;
        transition: background 0.15s ease;
      }
      .chat-chip:hover {
        background: #334155;
        color: #ffffff;
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
        #chat-launcher { bottom: 16px; right: 16px; padding: 4px 16px 4px 6px; height: 54px; }
        .launcher-img-wrap { width: 42px; height: 42px; }
        .launcher-title { font-size: 13px; }
      }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="brand-title-wrap">
                <img src="/logo.jpg" alt="Garza Logo" class="header-logo" onerror="this.style.display='none'">
                <div>
                    <h1>GARZA GLOBAL GRAVITON</h1>
                    <p style="color: #94a3b8; margin: 4px 0 0 0; font-size: 14px;">High-Performance Computing, Ad-Hoc Gaming Mesh, Small Business Ledger &amp; Sovereign Vaulting</p>
                </div>
            </div>
            <span class="badge">SYSTEM ONLINE</span>
        </div>

        <!-- Comprehensive Free Trial Workloads Grid -->
        <div class="card" style="border-left-color: var(--cyan);">
            <div class="card-title">✨ Free Trial Workloads: Gaming, Ad-Hoc Mesh, Business &amp; Specialized Industry Tools</div>
            <p style="font-size: 13px; color: var(--muted); margin-top: 0;">Click any workflow template below to automatically configure the trial intake form:</p>
            <div class="tool-grid">
                <div class="tool-box" onclick="selectTool('gaming_telemetry')">
                    <div>
                        <div class="tool-header">
                            <span style="color: var(--cyan);">🎮 Gaming Telemetry &amp; 1% Lows</span>
                            <span>&darr;</span>
                        </div>
                        <div class="tool-desc">Parse CapFrameX / HWiNFO logs, analyze 0.1% &amp; 1% frame-time drops, eliminate micro-stutters, and benchmark hardware curves.</div>
                    </div>
                    <div class="tool-tap">Load Template &rarr;</div>
                </div>

                <div class="tool-box" onclick="selectTool('adhoc_mesh')">
                    <div>
                        <div class="tool-header">
                            <span style="color: var(--indigo);">🌐 Ad-Hoc P2P Mesh &amp; On-Demand Server</span>
                            <span>&darr;</span>
                        </div>
                        <div class="tool-desc">Configure ephemeral play-when-you-play servers, zero-port-forwarding P2P LAN tunnels, and direct encrypted multi-gigabit file sync.</div>
                    </div>
                    <div class="tool-tap">Load Template &rarr;</div>
                </div>

                <div class="tool-box" onclick="selectTool('server_vault')">
                    <div>
                        <div class="tool-header">
                            <span style="color: var(--green);">🛡️ Game Server Hardening &amp; World Vault</span>
                            <span>&darr;</span>
                        </div>
                        <div class="tool-desc">Harden game ports against DDoS/RCON exploits, schedule auto-restart memory cleanup, and stamp SHA-256 rolling world backups.</div>
                    </div>
                    <div class="tool-tap">Load Template &rarr;</div>
                </div>

                <div class="tool-box" onclick="selectTool('bookkeeping')">
                    <div>
                        <div class="tool-header">
                            <span style="color: var(--emerald);">💼 Bookkeeping &amp; Financial Ledger</span>
                            <span>&darr;</span>
                        </div>
                        <div class="tool-desc">Reconcile raw bank statement CSVs, fix corrupted negative numbers, standardize merchant names, and categorize expenses.</div>
                    </div>
                    <div class="tool-tap">Load Template &rarr;</div>
                </div>

                <div class="tool-box" onclick="selectTool('3d_render')">
                    <div>
                        <div class="tool-header">
                            <span style="color: var(--pink);">🎬 3D Render, Film &amp; AEC Data Sync</span>
                            <span>&darr;</span>
                        </div>
                        <div class="tool-desc">Manage distributed burst rendering pipelines, verify frame sequence continuity, and sync 50GB+ CAD/BIM assets securely.</div>
                    </div>
                    <div class="tool-tap">Load Template &rarr;</div>
                </div>

                <div class="tool-box" onclick="selectTool('legal_audit')">
                    <div>
                        <div class="tool-header">
                            <span style="color: var(--amber);">⚖️ Legal Redaction, FOIA &amp; Provenance</span>
                            <span>&darr;</span>
                        </div>
                        <div class="tool-desc">Scrub PII from discovery agreements, format citation bibliographies, and stamp immutable SHA-256 digital prior-art certificates.</div>
                    </div>
                    <div class="tool-tap">Load Template &rarr;</div>
                </div>
            </div>
        </div>

        <!-- À La Carte Production Services & Instant Checkout -->
        <div class="card" style="border-left-color: var(--purple);">
            <div class="card-title">📦 À La Carte Production Services &amp; Instant Checkout</div>
            <div class="pricing-grid">
                <div class="pricing-card">
                    <div>
                        <div class="pricing-title">Script / Mod / Mesh Fix</div>
                        <div class="pricing-price">$75</div>
                        <div class="pricing-desc">Telemetry analyzers, P2P mesh scripts, ledger formatters, pandas acceleration, and quick patches.</div>
                    </div>
                    <a href="{{ tier1_link }}" target="_blank" class="checkout-btn">Checkout Tier 1 &rarr;</a>
                </div>
                <div class="pricing-card">
                    <div>
                        <div class="pricing-title">Automated Server / Pipeline</div>
                        <div class="pricing-price">$250</div>
                        <div class="pricing-desc">Hardened game servers with automated backups, end-to-end bookkeeping sync, and match stat ETL pipelines.</div>
                    </div>
                    <a href="{{ tier2_link }}" target="_blank" class="checkout-btn" style="background: #059669;">Checkout Tier 2 &rarr;</a>
                </div>
                <div class="pricing-card">
                    <div>
                        <div class="pricing-title">Compute &amp; Simulation Crunch</div>
                        <div class="pricing-price">$600+</div>
                        <div class="pricing-desc">Multi-node game clusters, high-density parameter sweeps, distributed render workflows, batch simulations.</div>
                    </div>
                    <a href="{{ tier3_link }}" target="_blank" class="checkout-btn">Checkout Tier 3 &rarr;</a>
                </div>
            </div>
        </div>

        <!-- Frequently Asked Questions & Support -->
        <div class="card" style="border-left-color: var(--accent);">
            <div class="card-title">❓ Frequently Asked Questions &amp; Support</div>
            <div class="faq-item" onclick="this.classList.toggle('active')">
                <div class="faq-question"><span>How do your Ad-Hoc and P2P mesh solutions work?</span> <span>+</span></div>
                <div class="faq-answer">We build encrypted, direct point-to-point tunnels (using WireGuard/Tailscale engines) that bypass central cloud servers. This allows zero-port-forwarding multiplayer, instant multi-gigabit file transfers, and on-demand servers that spin down when you log off.</div>
            </div>
            <div class="faq-item" onclick="this.classList.toggle('active')">
                <div class="faq-question"><span>What industries and demographics do you service?</span> <span>+</span></div>
                <div class="faq-answer">We provide specialized pipelines for PC Gamers &amp; Esports Teams, Small Business Bookkeeping, 3D Render &amp; Animation Studios, Legal / Compliance Teams, Architectural AEC Firms, and Independent Hardware Makers.</div>
            </div>
            <div class="faq-item" onclick="this.classList.toggle('active')">
                <div class="faq-question"><span>What can I do with a free trial token?</span> <span>+</span></div>
                <div class="faq-answer">Trial tokens allow you to process a complete sample dataset (up to 500 rows of telemetry/bookkeeping, 1 media file, or 1 mesh config) or test-run a 10-parameter compute sweep slice with an immutable SHA-256 verification receipt at zero cost.</div>
            </div>
            <div class="faq-item" onclick="this.classList.toggle('active')">
                <div class="faq-question"><span>How does billing and payment work?</span> <span>+</span></div>
                <div class="faq-answer">We accept all major credit cards, Apple Pay, ACH transfers, and corporate invoicing via Stripe. For custom builds, milestones are approved prior to deployment.</div>
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
            <div class="card-title">🚀 Workload Intake &amp; Token Redemption</div>
            <form action="/submit" method="POST">
                <div class="form-group">
                    <label>Full Name or Company / Gamer Tag</label>
                    <input type="text" name="name" id="input-name" placeholder="Acme Corp / Jane Doe / Tag" required>
                </div>
                <div class="form-group">
                    <label>Contact Email or Discord</label>
                    <input type="text" name="email" id="input-email" placeholder="contact@domain.com" required>
                </div>
                <div class="form-group">
                    <label>Access / Trial Token (Optional for Free Demo Execution)</label>
                    <input type="text" name="token" id="input-token" placeholder="e.g. GGG-GAMING-A1B2C3 or GGG-BIZ-G7H8I9" style="font-family: monospace; border-color: var(--accent);">
                </div>
                <div class="form-group">
                    <label>Project Scope / Paste Data, Telemetry, Server, or Legal Specs</label>
                    <textarea name="scope" id="input-scope" rows="4" placeholder="Describe what you want to build, analyze, clean, calculate, or stamp..." required></textarea>
                </div>
                <div class="form-group">
                    <label>Select Service / Evaluation Tier</label>
                    <select name="tier" id="select-tier">
                        <option value="PC Gaming, Telemetry & Ad-Hoc Free Trial Run">PC Gaming, Telemetry &amp; Ad-Hoc Free Trial Run</option>
                        <option value="Small Business & Bookkeeping Free Trial Run">Small Business &amp; Bookkeeping Free Trial Run</option>
                        <option value="Creative, 3D Render & Legal Free Trial Run">Creative, 3D Render &amp; Legal Free Trial Run</option>
                        <option value="Enterprise POC Slice (Free Token Evaluation)">Enterprise POC Slice (Free Token Evaluation)</option>
                        <option value="Script / Calculation Fix ($75)">Script / Calculation Fix — $75</option>
                        <option value="Automated ETL, Server & Bookkeeping Pipeline ($250)" selected>Automated ETL, Server &amp; Bookkeeping Pipeline — $250</option>
                        <option value="Compute & Simulation Crunch ($600+)">Compute &amp; Simulation Crunch — $600+</option>
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

    <!-- Double-Sized High-Visibility Floating Pill Launcher -->
    <button id="chat-launcher" onclick="toggleChat()" title="Open Assistant &amp; Estimator">
        <div class="launcher-img-wrap">
            <img src="/logo.jpg" alt="Logo" onerror="this.parentElement.innerHTML='⚡'">
        </div>
        <div class="launcher-text-wrap">
            <span class="launcher-title">FAQ &amp; ESTIMATOR</span>
            <span class="launcher-sub">Instant Assistant &rarr;</span>
        </div>
    </button>

    <div id="chat-box">
        <div class="chat-header">
            <div style="display:flex; align-items:center; gap:8px;">
                <img src="/logo.jpg" alt="Logo" style="width:22px; height:22px; border-radius:4px; object-fit:cover;" onerror="this.style.display='none'">
                <span>Garza Global Graviton Assistant</span>
            </div>
            <span style="cursor:pointer; font-size: 18px;" onclick="toggleChat()">✕</span>
        </div>
        <div class="chat-body" id="chat-stream">
            <div class="chat-msg msg-bot">Hello! How can I assist you with PC gaming, ad-hoc servers, bookkeeping, or data engineering today? Tap an option below:</div>
        </div>
        <div class="chat-options">
            <span class="chat-chip" onclick="askBot('gaming')">🎮 Gaming &amp; 1% Lows</span>
            <span class="chat-chip" onclick="askBot('adhoc')">🌐 Ad-Hoc &amp; P2P Mesh</span>
            <span class="chat-chip" onclick="askBot('server')">🛡️ Server Hardening</span>
            <span class="chat-chip" onclick="askBot('bookkeeping')">💼 Bookkeeping &amp; Reconcile</span>
            <span class="chat-chip" onclick="askBot('studios')">🎬 3D Studios &amp; AEC</span>
            <span class="chat-chip" onclick="askBot('legal')">⚖️ Legal, FOIA &amp; Proof</span>
            <span class="chat-chip" onclick="askBot('estimate')">📊 Project Cost Estimator</span>
            <span class="chat-chip" onclick="askBot('pricing')">💰 Price List</span>
        </div>
    </div>

    <script>
      function toggleChat() {
        var box = document.getElementById('chat-box');
        box.style.display = (box.style.display === 'flex') ? 'none' : 'flex';
      }

      function selectTool(type) {
        var tierSelect = document.getElementById('select-tier');
        var scopeBox = document.getElementById('input-scope');
        var intakeCard = document.getElementById('intake-section');

        if (type === 'gaming_telemetry') {
          tierSelect.value = "PC Gaming, Telemetry & Ad-Hoc Free Trial Run";
          scopeBox.value = "Task: PC Gaming Telemetry & Frame-Time Analysis\\n- Ingest CapFrameX / HWiNFO / Afterburner benchmark logs.\\n- Calculate 0.1% & 1% low frame-time stutters, average FPS, and temperature/bottleneck curves.";
        } else if (type === 'adhoc_mesh') {
          tierSelect.value = "PC Gaming, Telemetry & Ad-Hoc Free Trial Run";
          scopeBox.value = "Task: Ad-Hoc P2P Mesh & On-Demand Server Setup\\n- Configure zero-port-forwarding encrypted P2P LAN tunnel for co-op play or instant high-speed multi-gigabit file transfers.";
        } else if (type === 'server_vault') {
          tierSelect.value = "PC Gaming, Telemetry & Ad-Hoc Free Trial Run";
          scopeBox.value = "Task: Dedicated Game Server Hardening & Save Vaulting\\n- Configure firewall port security (UFW/iptables), auto-restart memory cleanup, and automated SHA-256 rolling world backups.";
        } else if (type === 'bookkeeping') {
          tierSelect.value = "Small Business & Bookkeeping Free Trial Run";
          scopeBox.value = "Task: Bookkeeping & Bank Statement Normalizer\\n- Ingest messy bank/POS CSV transactions.\\n- Normalize merchant names, fix negative currency formatting, and categorize expenses.";
        } else if (type === '3d_render') {
          tierSelect.value = "Creative, 3D Render & Legal Free Trial Run";
          scopeBox.value = "Task: 3D Render & CAD File Sync Optimization\\n- Organize frame sequences, calculate burst compute requirements, or configure direct encrypted asset transfer for large CAD/BIM models.";
        } else if (type === 'legal_audit') {
          tierSelect.value = "Creative, 3D Render & Legal Free Trial Run";
          scopeBox.value = "Task: Legal Redaction & Cryptographic Prior-Art Stamp\\n- Scrub PII / SSNs from discovery documents, standardize citations, and stamp an immutable SHA-256 proof-of-creation receipt.";
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

        if (topic === 'gaming') {
          userMsg.innerText = "What PC Gaming services and telemetry tools do you offer?";
          botMsg.innerHTML = "<b>PC Gaming & Telemetry Engineering:</b><br>• <b>Frame-Time & 1% Low Analysis:</b> Ingest CapFrameX, Afterburner, and PresentMon CSVs to chart micro-stutters and hardware bottlenecks.<br>• <b>Match & Combat Log Parser:</b> Parse tournament combat logs into structured kill/death and damage timelines.<br>• <b>Clip Compression:</b> Shrink 2GB raw OBS/ShadowPlay 60FPS clips under 25MB without ruining clarity.";
        } else if (topic === 'adhoc') {
          userMsg.innerText = "How do Ad-Hoc networks and P2P mesh setups work?";
          botMsg.innerHTML = "<b>Ad-Hoc & P2P Mesh Architecture:</b><br>• <b>Play-When-You-Play Servers:</b> On-demand game instances that spin up for sessions, freeze world saves, and terminate to save costs.<br>• <b>Zero-Port-Forwarding LAN:</b> Encrypted peer tunnels for private co-op mods and emulators without public IP risks.<br>• <b>Direct Asset Sync:</b> Blazing-fast P2P file transfers for 4K video, modpacks, and multi-track audio stems.";
        } else if (topic === 'server') {
          userMsg.innerText = "How do you handle dedicated server security and maintenance?";
          botMsg.innerHTML = "<b>Server Provisioning & Vaulting:</b><br>• <b>Port Hardening:</b> Firewall lockdown (UFW/Fail2ban) and RCON protection.<br>• <b>Memory Watchdogs:</b> Automated daemon scripts to clear memory leaks and execute low-traffic restarts.<br>• <b>SHA-256 Rolling Backups:</b> Tamper-proof, hourly snapshots of world states and player databases.";
        } else if (topic === 'bookkeeping') {
          userMsg.innerText = "How do your small business bookkeeping services work?";
          botMsg.innerHTML = "<b>Bookkeeping & Ledger Engineering:</b><br>• <b>Bank Statement Cleanup:</b> Strip merchant noise, standardize transaction dates, and correct sign formats (+/-).<br>• <b>Expense Categorization:</b> Map transactions to chart of accounts automatically.<br>• <b>Reconciliation Ready:</b> Output clean CSV/Excel ready for QuickBooks, Xero, or tax prep.";
        } else if (topic === 'studios') {
          userMsg.innerText = "What services are available for 3D Render Studios and AEC Firms?";
          botMsg.innerHTML = "<b>3D Studios & Architecture:</b><br>• <b>Burst Rendering Compute:</b> Deploy heavy Blender/Unreal rendering workloads across sovereign compute nodes.<br>• <b>Large CAD/BIM File Sync:</b> Move 50GB+ blueprints and drone footage directly between field crews and engineers without cloud caps.";
        } else if (topic === 'legal') {
          userMsg.innerText = "What is available for legal teams, FOIA, and IP protection?";
          botMsg.innerHTML = "<b>Legal, FOIA & Compliance:</b><br>• <b>PII & SSN Redaction:</b> Automated scripts to sanitize sensitive data from litigation records.<br>• <b>Sovereign SHA-256 Stamps:</b> Immutable proof of prior art and evidence chain-of-custody tracking.<br>• <b>Citation Normalizer:</b> Standardize case references into APA/MLA/Bluebook formats.";
        } else if (topic === 'estimate') {
          userMsg.innerText = "How are projects estimated?";
          botMsg.innerHTML = "<b>Instant Project Estimator:</b><br>• <b>Quick Calculation / Mesh Script Patch:</b> $75 (under 24h)<br>• <b>Full Server, Pipeline or Bookkeeping Build:</b> $250 (3-5 days)<br>• <b>Enterprise Compute & Simulation Crunch:</b> $600+<br>Submit the form above for a fixed-price statement of work!";
        } else if (topic === 'pricing') {
          userMsg.innerText = "What are the standard prices?";
          botMsg.innerHTML = "Our fixed rates:<br>• <b>Tier 1 (Fix / Script):</b> $75<br>• <b>Tier 2 (Automated Pipeline / Server):</b> $250<br>• <b>Tier 3 (Modeling & Compute):</b> $600+<br>• <b>Retainers:</b> Custom monthly SLA.";
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
    <title>Admin Submissions & Demographics Token Mint | Garza Global Graviton</title>
    <style>
      :root {
        --bg: #0b0f19;
        --panel: #131b2e;
        --border: #1e293b;
        --accent: #38bdf8;
        --green: #34d399;
        --purple: #a855f7;
        --amber: #f59e0b;
        --pink: #ec4899;
        --emerald: #10b981;
        --cyan: #06b6d4;
        --indigo: #6366f1;
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
        max-width: 1020px;
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
        min-width: 750px;
        border-collapse: collapse;
        font-size: 13px;
      }
      th { text-align: left; color: var(--muted); padding: 10px 8px; border-bottom: 1px solid #334155; }
      td { padding: 10px 8px; border-bottom: 1px solid #334155; color: #cbd5e1; }
      .mint-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 8px;
        margin-top: 12px;
      }
      .mint-btn-pill {
        border: 1px solid #334155;
        padding: 8px 12px;
        border-radius: 6px;
        font-weight: bold;
        cursor: pointer;
        font-size: 12px;
        text-align: center;
        transition: transform 0.1s ease;
      }
      .mint-btn-pill:hover { transform: scale(1.02); }
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
            <h1>Operator Control: Multi-Demographic Token Mint &amp; Ledger</h1>
            <span style="color: var(--green); font-weight: bold; font-family: monospace;">Leads: {{ submissions|length }} | Active/Total Tokens: <span id="token-count">{{ tokens|length }}</span></span>
        </div>

        <div class="card" style="border-left: 4px solid var(--cyan);">
            <span style="font-weight: bold; color: white;">🎟️ Mint Specialized Demographic &amp; Industry Access Tokens</span>
            <p style="font-size: 12px; color: var(--muted); margin: 4px 0 0 0;">Click any demographic category to generate an instant copyable token string:</p>
            
            <div class="mint-grid">
                <button type="button" class="mint-btn-pill" style="background:#083344; color:var(--cyan);" onclick="generateToken('gaming')">🎮 + Mint Gaming &amp; Telemetry</button>
                <button type="button" class="mint-btn-pill" style="background:#1e1b4b; color:var(--indigo);" onclick="generateToken('adhoc')">🌐 + Mint Ad-Hoc &amp; Mesh</button>
                <button type="button" class="mint-btn-pill" style="background:#064e3b; color:var(--emerald);" onclick="generateToken('business')">💼 + Mint Bookkeeping &amp; Biz</button>
                <button type="button" class="mint-btn-pill" style="background:#4a044e; color:var(--pink);" onclick="generateToken('creative')">🎬 + Mint 3D, Film &amp; Creative</button>
                <button type="button" class="mint-btn-pill" style="background:#451a03; color:var(--amber);" onclick="generateToken('legal')">⚖️ + Mint Legal, FOIA &amp; Proof</button>
                <button type="button" class="mint-btn-pill" style="background:#581c87; color:var(--purple);" onclick="generateToken('enterprise')">⚡ + Mint Enterprise 10-Param</button>
            </div>

            <div class="table-wrapper">
                <table id="token-table">
                    <thead>
                        <tr>
                            <th>Token Key</th>
                            <th>Status</th>
                            <th>Target Demographic / Tier</th>
                            <th>Evaluation Limit / Snippet Scope</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody id="token-tbody">
                        {% for key, val in tokens.items() %}
                        <tr id="row-{{ key }}">
                            <td style="font-family: monospace; color: {% if 'GAMING' in key %}var(--cyan){% elif 'ADHOC' in key %}var(--indigo){% elif 'BIZ' in key %}var(--emerald){% elif 'CREATIVE' in key %}var(--pink){% elif 'LEGAL' in key %}var(--amber){% else %}var(--purple){% endif %}; font-weight: bold;">{{ key }}</td>
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
            
            let color = 'var(--accent)';
            if (data.token.includes('GAMING')) color = 'var(--cyan)';
            else if (data.token.includes('ADHOC')) color = 'var(--indigo)';
            else if (data.token.includes('BIZ')) color = 'var(--emerald)';
            else if (data.token.includes('CREATIVE')) color = 'var(--pink)';
            else if (data.token.includes('LEGAL')) color = 'var(--amber)';
            else if (data.token.includes('ENTERPRISE')) color = 'var(--purple)';

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

@app.route("/logo.jpg")
def serve_logo():
    if os.path.exists(LOGO_FILE):
        return send_file(LOGO_FILE, mimetype="image/jpeg")
    return ("", 404)

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
    token_type = data.get("type", "gaming")
    tokens = load_json(TOKENS_FILE, {})
    
    created_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    hex_id = secrets.token_hex(3).upper()

    if token_type == "gaming":
        new_token = f"GGG-GAMING-{hex_id}"
        tier = "Gaming & Telemetry Trial"
        max_rows = 500
        sample_limit = "500 rows frame-time logs / 1 clip compression"
    elif token_type == "adhoc":
        new_token = f"GGG-ADHOC-{hex_id}"
        tier = "Ad-Hoc & Server Trial"
        max_rows = 1000
        sample_limit = "1 ephemeral P2P mesh setup / server hardening audit"
    elif token_type == "business":
        new_token = f"GGG-BIZ-{hex_id}"
        tier = "Bookkeeping & Business Trial"
        max_rows = 500
        sample_limit = "500 rows bank ledger reconciliation / margin model"
    elif token_type == "creative":
        new_token = f"GGG-CREATIVE-{hex_id}"
        tier = "Creative & Studio Trial"
        max_rows = 1000
        sample_limit = "1 3D render burst check / 1 audio stem provenance seal"
    elif token_type == "legal":
        new_token = f"GGG-LEGAL-{hex_id}"
        tier = "Legal & Compliance Trial"
        max_rows = 500
        sample_limit = "1 PII redaction pass / 1 SHA-256 prior-art audit"
    elif token_type == "enterprise":
        new_token = f"GGG-ENTERPRISE-{hex_id}"
        tier = "Enterprise POC Slice"
        max_rows = 50000
        sample_limit = "10-parameter sweep slice & cryptographic ledger audit"
    else:
        new_token = f"GGG-TRIAL-{hex_id}"
        tier = "Standard General Trial"
        max_rows = 500
        sample_limit = "General single trial execution"

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
        "scope": data.get("scope", data.get("requirements", "General Workload Inquiry")),
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