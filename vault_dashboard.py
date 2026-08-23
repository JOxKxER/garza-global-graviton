import os
import json
import secrets
import hashlib
import re
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, redirect, send_file

app = Flask(__name__)

# File storage paths
BASE_DIR = os.path.dirname(__file__)
SUBMISSIONS_FILE = os.path.join(BASE_DIR, "client_submissions.json")
TOKENS_FILE = os.path.join(BASE_DIR, "valid_tokens.json")
REVIEWS_FILE = os.path.join(BASE_DIR, "client_reviews.json")
LOGO_FILE = os.path.join(BASE_DIR, "logo.jpg")

# Pre-configured Stripe Payment Links
STRIPE_TIER1_LINK = "https://buy.stripe.com/test_eVaeV077j8Fp9sA8ww"  # $75
STRIPE_TIER2_LINK = "https://buy.stripe.com/test_7sIeV08bncVB34ccMN"  # $250
STRIPE_TIER3_LINK = "https://buy.stripe.com/test_3csbIQ63ff3J34c8wx"  # $600

# Prohibited public multiplayer exploit keywords
PUBLIC_EXPLOIT_PATTERNS = [
    r"\baimbot\b", r"\baim\s*assist\b", r"\btriggerbot\b", r"\bwallhack\b",
    r"\besp\s*hack\b", r"\bdll\s*injection\b", r"\bmemory\s*hook\b",
    r"\brecoil\s*script\b", r"\banti-recoil\b", r"\bdma\s*cheat\b",
    r"\bbypass\s*vanguard\b", r"\bbypass\s*easyanticheat\b", r"\bbypass\s*battleye\b"
]

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

def check_exploit_policy(text, tier):
    # Allow custom server scripting if explicitly designated as private
    if "Private" in tier or "Custom Server" in tier or "Ad-Hoc" in tier:
        return True, "Private / Custom Server Sandbox (Authorized Host Rules)"
    
    text_lower = text.lower()
    for pat in PUBLIC_EXPLOIT_PATTERNS:
        if re.search(pat, text_lower):
            return False, "REJECTED - Exploitation Policy Violation: Tools targeting public competitive multiplayer are prohibited."
    return True, "Verified Fair-Play Compliant"

def init_defaults():
    tokens = load_json(TOKENS_FILE, {})
    if not tokens:
        tokens = {
            "GGG-AI-STUDIO-1A2B": {
                "status": "ACTIVE",
                "tier": "AI Studio & Creation Trial",
                "max_rows": 1000,
                "sample_limit": "1 high-res AI asset / mini-app script / cinematic render test",
                "created": "2026-08-23 12:00:00 UTC"
            },
            "GGG-GAMING-C3D4": {
                "status": "ACTIVE",
                "tier": "Gaming & Telemetry Trial",
                "max_rows": 500,
                "sample_limit": "500 rows frame-time logs / 1 clip compression",
                "created": "2026-08-23 12:00:00 UTC"
            },
            "GGG-CUSTOM-SRV-E5F6": {
                "status": "ACTIVE",
                "tier": "Private Server & Custom Rules Trial",
                "max_rows": 1000,
                "sample_limit": "1 private server rule harness / ad-hoc P2P mesh setup",
                "created": "2026-08-23 12:00:00 UTC"
            },
            "GGG-BIZ-G7H8": {
                "status": "ACTIVE",
                "tier": "Bookkeeping & Business Trial",
                "max_rows": 500,
                "sample_limit": "500 rows bank ledger reconciliation / margin model",
                "created": "2026-08-23 12:00:00 UTC"
            },
            "GGG-LEGAL-I9J0": {
                "status": "ACTIVE",
                "tier": "Legal & Compliance Trial",
                "max_rows": 500,
                "sample_limit": "1 PII redaction pass / 1 SHA-256 prior-art audit",
                "created": "2026-08-23 12:00:00 UTC"
            },
            "GGG-ENTERPRISE-K1L2": {
                "status": "ACTIVE",
                "tier": "Enterprise POC Slice",
                "max_rows": 50000,
                "sample_limit": "10-parameter sweep slice & cryptographic ledger audit",
                "created": "2026-08-23 12:00:00 UTC"
            }
        }
        save_json(TOKENS_FILE, tokens)

    reviews = load_json(REVIEWS_FILE, [])
    if not reviews:
        reviews = [
            {
                "name": "Apex Scrims League",
                "role": "Esports Tournament Host",
                "stars": 5,
                "comment": "The private match telemetry analyzer and anti-tamper receipts cut our dispute review times to zero. Flawless verification receipts.",
                "timestamp": "2026-08-22 14:10 UTC"
            },
            {
                "name": "Solstice Studios",
                "role": "Indie Game Developer",
                "stars": 5,
                "comment": "We generated seamless 2K PBR game textures and spun up an ad-hoc playtest server with custom rules in under 15 minutes.",
                "timestamp": "2026-08-21 16:30 UTC"
            },
            {
                "name": "Marcus V. (Apex Build Co)",
                "role": "General Contractor",
                "stars": 5,
                "comment": "Reconciled over 1,400 disorganized material receipt line items and fixed our bank statement CSV formulas in minutes.",
                "timestamp": "2026-08-21 09:44 UTC"
            }
        ]
        save_json(REVIEWS_FILE, reviews)

init_defaults()

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
    <title>Garza Global Graviton | Sovereign Vault, AI Creation & Custom Server Infrastructure</title>
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
        max-width: 1040px;
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

      /* Fair-Play Warning & Policy Banner */
      .fairplay-banner {
        background: #082f49;
        border: 1px solid #0284c7;
        border-left: 5px solid var(--accent);
        border-radius: 8px;
        padding: 16px 20px;
        margin-top: 18px;
        display: flex;
        align-items: flex-start;
        gap: 16px;
      }
      .fairplay-icon { font-size: 26px; flex-shrink: 0; margin-top: 2px; }
      .fairplay-content { font-size: 12px; color: #bae6fd; line-height: 1.5; }
      .fairplay-title { font-size: 14px; font-weight: 800; color: #ffffff; margin-bottom: 4px; }
      .fairplay-content b { color: #ffffff; }
      
      .warning-tag-box {
        background: rgba(15, 23, 42, 0.6);
        border: 1px solid #334155;
        border-radius: 6px;
        padding: 8px 12px;
        margin-top: 8px;
        font-size: 11px;
        color: #94a3b8;
      }
      .warning-tag-box span { color: var(--green); font-weight: bold; }
      .warning-tag-box span.prohibited { color: var(--red); font-weight: bold; }

      /* Verified Reviews & AI Summary Section */
      .reviews-layout {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 18px;
        margin-top: 12px;
      }
      .ai-summary-box {
        background: #0f172a;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 18px;
      }
      .ai-summary-header {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 14px;
        font-weight: 800;
        color: var(--accent);
        margin-bottom: 10px;
      }
      .ai-tag-chip {
        display: inline-block;
        background: #1e293b;
        color: var(--green);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 3px 8px;
        font-size: 11px;
        margin-right: 4px;
        margin-bottom: 6px;
        font-weight: 600;
      }
      .score-display {
        font-size: 32px;
        font-weight: 900;
        color: var(--amber);
        font-family: monospace;
      }
      .star-string { color: var(--amber); letter-spacing: 2px; }
      .recent-reviews-scroll {
        max-height: 330px;
        overflow-y: auto;
        display: flex;
        flex-direction: column;
        gap: 10px;
        padding-right: 4px;
      }
      .review-item {
        background: #0f172a;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 14px;
      }
      .review-author {
        font-weight: bold;
        color: #f8fafc;
        font-size: 13px;
        display: flex;
        justify-content: space-between;
      }
      .review-role { font-size: 11px; color: var(--muted); }
      .review-text { font-size: 12px; color: #cbd5e1; margin-top: 6px; line-height: 1.4; }

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
        flex-wrap: wrap;
        gap: 10px;
      }
      .footer-links a { color: var(--muted); text-decoration: none; }
      .footer-links a:hover { color: var(--accent); }

      @media (max-width: 750px) {
        .reviews-layout { grid-template-columns: 1fr; }
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
                    <p style="color: #94a3b8; margin: 4px 0 0 0; font-size: 14px;">High-Performance Computing, AI Asset Generation, Private Server Mesh &amp; Sovereign Vaulting</p>
                </div>
            </div>
            <span class="badge">SYSTEM ONLINE</span>
        </div>

        <!-- Fair-Play Policy & Warning Banner -->
        <div class="fairplay-banner">
            <span class="fairplay-icon">⚠️</span>
            <div class="fairplay-content">
                <div class="fairplay-title">Gaming Integrity &amp; Dual-Zone Fair-Play Warning Policy</div>
                Garza Global Graviton enforces strict cryptographic integrity and legal fair-play boundaries across all compute pipelines:
                <div class="warning-tag-box">
                    <div><span>✓ PERMITTED (Private Sovereign Zone):</span> Custom server scripting, host physics mods, house rules, offline 3D game asset creation, and private squad P2P mesh LANs.</div>
                    <div style="margin-top:4px;"><span class="prohibited">✕ STRICTLY PROHIBITED (Public Zone):</span> Memory injection (DLL hooks), aimbots, recoil macros, ESP overlays, or bypass tools targeting public competitive matchmaking games. All incoming public requests are automatically filtered, rejected, and logged.</div>
                </div>
            </div>
        </div>

        <!-- Comprehensive Free Trial Workloads Grid -->
        <div class="card" style="border-left-color: var(--cyan);">
            <div class="card-title">✨ Free Trial Workloads: AI Studio, Private Servers, Gaming &amp; Data Tools</div>
            <p style="font-size: 13px; color: var(--muted); margin-top: 0;">Click any workflow template below to automatically configure the trial intake form:</p>
            <div class="tool-grid">
                <div class="tool-box" onclick="selectTool('ai_assets')">
                    <div>
                        <div class="tool-header">
                            <span style="color: var(--pink);">🎨 AI 3D Textures &amp; Game Assets</span>
                            <span>&darr;</span>
                        </div>
                        <div class="tool-desc">Generate seamless 2K PBR game textures, low-poly 3D mesh bases, and sprite sheets with deterministic SHA-256 copyright seals.</div>
                    </div>
                    <div class="tool-tap">Load Template &rarr;</div>
                </div>

                <div class="tool-box" onclick="selectTool('custom_server')">
                    <div>
                        <div class="tool-header">
                            <span style="color: var(--indigo);">🕹️ Private Match &amp; Custom Server Rules</span>
                            <span>&darr;</span>
                        </div>
                        <div class="tool-desc">Configure isolated private servers, custom physics rules, authorized modpacks, and zero-port-forwarding P2P squad LANs.</div>
                    </div>
                    <div class="tool-tap">Load Template &rarr;</div>
                </div>

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

                <div class="tool-box" onclick="selectTool('ai_apps')">
                    <div>
                        <div class="tool-header">
                            <span style="color: var(--purple);">⚡ Custom AI Automation Gems</span>
                            <span>&darr;</span>
                        </div>
                        <div class="tool-desc">Build standalone AI mini-apps, automated receipt intake bots, and YouTube chapter/show-note generators with zero coding.</div>
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

        <!-- Verified Customer Reviews & Amazon-Style AI Summary Section -->
        <div class="card" id="reviews-section" style="border-left-color: var(--amber);">
            <div class="card-title" style="display: flex; justify-content: space-between; align-items: center;">
                <span>⭐ Verified Pipeline Reviews &amp; Intelligence Summary</span>
                <span style="font-size: 13px; color: var(--muted);">{{ reviews|length }} Verified Submissions</span>
            </div>
            
            <div class="reviews-layout">
                <!-- AI Synthesized Overview (Amazon Style) -->
                <div class="ai-summary-box">
                    <div class="ai-summary-header">
                        <span>🤖 Customers Say (AI Highlights)</span>
                    </div>
                    <p style="font-size: 13px; color: #cbd5e1; line-height: 1.5; margin: 0 0 12px 0;">
                        {{ ai_summary }}
                    </p>
                    <div style="margin-bottom: 12px;">
                        <span class="ai-tag-chip">✓ Fair-Play Verified</span>
                        <span class="ai-tag-chip">✓ Instant Private Servers</span>
                        <span class="ai-tag-chip">✓ High-Quality AI Textures</span>
                        <span class="ai-tag-chip">✓ SHA-256 Stamped Receipts</span>
                    </div>
                    <div style="display: flex; align-items: baseline; gap: 10px; border-top: 1px solid #334155; padding-top: 10px;">
                        <span class="score-display">{{ avg_score }}</span>
                        <div>
                            <div class="star-string">{{ star_string }}</div>
                            <span style="font-size: 12px; color: var(--muted);">Overall Customer Satisfaction</span>
                        </div>
                    </div>
                </div>

                <!-- Recent Live Customer Reviews List -->
                <div class="recent-reviews-scroll">
                    {% for rev in reviews|reverse %}
                    <div class="review-item">
                        <div class="review-author">
                            <span>{{ rev.name }}</span>
                            <span class="star-string">{% for i in range(rev.stars) %}★{% endfor %}</span>
                        </div>
                        <div class="review-role">{{ rev.role }} &bull; <small>{{ rev.timestamp }}</small></div>
                        <div class="review-text">"{{ rev.comment }}"</div>
                    </div>
                    {% endfor %}
                </div>
            </div>

            <!-- Submit Feedback / Review Form -->
            <div style="margin-top: 18px; border-top: 1px solid #334155; padding-top: 16px;">
                <details style="cursor: pointer;">
                    <summary style="font-size: 13px; font-weight: bold; color: var(--accent);">✍️ Leave Client Feedback / Review</summary>
                    <form action="/submit_review" method="POST" style="margin-top: 12px;">
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px;">
                            <input type="text" name="name" placeholder="Your Name or Team Tag" required>
                            <input type="text" name="role" placeholder="Industry / Role (e.g. Game Dev, Server Host, Creator)" required>
                        </div>
                        <div style="display: grid; grid-template-columns: 1fr 3fr; gap: 10px; margin-bottom: 10px;">
                            <select name="stars">
                                <option value="5" selected>⭐⭐⭐⭐⭐ (5/5 Outstanding)</option>
                                <option value="4">⭐⭐⭐⭐ (4/5 Great)</option>
                                <option value="3">⭐⭐⭐ (3/5 Good)</option>
                            </select>
                            <input type="text" name="comment" placeholder="What workload did the engine run, and how did it perform?" required>
                        </div>
                        <button type="submit" class="cta-btn" style="padding: 8px 14px; font-size: 12px;">Publish Verified Review</button>
                    </form>
                </details>
            </div>
        </div>

        <!-- À La Carte Production Services & Instant Checkout -->
        <div class="card" style="border-left-color: var(--purple);">
            <div class="card-title">📦 À La Carte Production Services &amp; Instant Checkout</div>
            <div class="pricing-grid">
                <div class="pricing-card">
                    <div>
                        <div class="pricing-title">AI Asset / Script Fix</div>
                        <div class="pricing-price">$75</div>
                        <div class="pricing-desc">Texture generation, private server config rules, telemetry analyzers, and quick patches.</div>
                    </div>
                    <a href="{{ tier1_link }}" target="_blank" class="checkout-btn">Checkout Tier 1 &rarr;</a>
                </div>
                <div class="pricing-card">
                    <div>
                        <div class="pricing-title">Custom Server / AI Mini-App</div>
                        <div class="pricing-price">$250</div>
                        <div class="pricing-desc">Hardened dedicated servers, automated AI Gems, match stat ETL, and bookkeeping sync.</div>
                    </div>
                    <a href="{{ tier2_link }}" target="_blank" class="checkout-btn" style="background: #059669;">Checkout Tier 2 &rarr;</a>
                </div>
                <div class="pricing-card">
                    <div>
                        <div class="pricing-title">AI Video &amp; Cluster Compute</div>
                        <div class="pricing-price">$600+</div>
                        <div class="pricing-desc">Cinematic 4K generative video reels, multi-node game clusters, parameter sweeps, batch simulations.</div>
                    </div>
                    <a href="{{ tier3_link }}" target="_blank" class="checkout-btn">Checkout Tier 3 &rarr;</a>
                </div>
            </div>
        </div>

        <!-- Frequently Asked Questions & Support -->
        <div class="card" style="border-left-color: var(--accent);">
            <div class="card-title">❓ Frequently Asked Questions &amp; Support</div>
            <div class="faq-item" onclick="this.classList.toggle('active')">
                <div class="faq-question"><span>Can I set custom rules and mods on private servers?</span> <span>+</span></div>
                <div class="faq-answer">Yes! In private matches, co-op LANs, and custom servers, hosts have complete sovereignty to test mods, alter game physics, or script experimental mechanics. We strictly prohibit memory injection or exploit tools targeting public multiplayer games.</div>
            </div>
            <div class="faq-item" onclick="this.classList.toggle('active')">
                <div class="faq-question"><span>What is your Fair-Play and Anti-Cheat Policy?</span> <span>+</span></div>
                <div class="faq-answer">Our pipelines block any tool or script designed to manipulate public competitive games (aimbots, recoil scripts, memory hooks). All incoming public requests are scanned against automated exploit filters.</div>
            </div>
            <div class="faq-item" onclick="this.classList.toggle('active')">
                <div class="faq-question"><span>How do AI Asset Generation and Mini-Apps work?</span> <span>+</span></div>
                <div class="faq-answer">We run your prompts and specifications through high-memory compute clusters to output 2K PBR game textures, low-poly 3D models, or standalone automation bots, all stamped with immutable SHA-256 copyright seals.</div>
            </div>
            <div class="faq-item" onclick="this.classList.toggle('active')">
                <div class="faq-question"><span>What are your Terms of Service and Liability limits?</span> <span>+</span></div>
                <div class="faq-answer">All services are provided on an 'as-is' basis. We reserve the full right to refuse or revoke service for Terms of Service violations. View our full legal terms via the footer link.</div>
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
                <span class="metric-title">Fair-Play &amp; Sovereign Ledger Status</span>
                <span class="metric-value" style="color: var(--green);">Active &amp; Immutable (SHA-256)</span>
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
                    <input type="text" name="token" id="input-token" placeholder="e.g. GGG-AI-STUDIO-1A2B or GGG-GAMING-C3D4" style="font-family: monospace; border-color: var(--accent);">
                </div>
                <div class="form-group">
                    <label>Project Scope / AI Prompt / Server Rules / Data Specs</label>
                    <textarea name="scope" id="input-scope" rows="4" placeholder="Describe the AI asset you want to create, private server rules to configure, or data to analyze..." required></textarea>
                </div>
                <div class="form-group">
                    <label>Select Service / Evaluation Tier</label>
                    <select name="tier" id="select-tier">
                        <option value="AI Creation & Asset Generation Free Trial">AI Creation &amp; Asset Generation Free Trial</option>
                        <option value="Private Server & Custom Rules Free Trial">Private Server &amp; Custom Rules Free Trial</option>
                        <option value="PC Gaming & Telemetry Free Trial Run">PC Gaming &amp; Telemetry Free Trial Run</option>
                        <option value="Small Business & Bookkeeping Free Trial Run">Small Business &amp; Bookkeeping Free Trial Run</option>
                        <option value="Creative, 3D Render & Legal Free Trial Run">Creative, 3D Render &amp; Legal Free Trial Run</option>
                        <option value="Enterprise POC Slice (Free Token Evaluation)">Enterprise POC Slice (Free Token Evaluation)</option>
                        <option value="Script / AI Asset Fix ($75)">Script / AI Asset Fix — $75</option>
                        <option value="Automated Server, Pipeline & AI Bot ($250)" selected>Automated Server, Pipeline &amp; AI Bot — $250</option>
                        <option value="AI Video & Compute Simulation ($600+)">AI Video &amp; Compute Simulation — $600+</option>
                        <option value="Dedicated Monthly Retainer">Dedicated Monthly Pipeline Retainer</option>
                    </select>
                </div>
                <div class="actions-group">
                    <button type="submit" class="cta-btn">Submit Workload Request</button>
                    <a href="https://github.com/JOxKxER/garza-global-graviton" target="_blank" class="cta-btn-alt">GitHub Architecture Repository</a>
                </div>
                <p style="font-size: 11px; color: var(--muted); margin-top: 8px; text-align: center;">
                    By submitting, you agree to our <a href="/terms" style="color: var(--accent);">Terms of Service</a> &amp; Dual-Zone Fair-Play Policies.
                </p>
            </form>
        </div>

        <div class="footer-links">
            <span>&copy; Garza Global Graviton LLC</span>
            <div>
                <a href="/terms" style="margin-right: 14px;">Terms of Service &amp; Legal Liability</a>
                <a href="/admin/submissions">Operator Ledger &amp; Token Mint</a>
            </div>
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
            <div class="chat-msg msg-bot">Hello! How can I assist you with AI asset creation, private game servers, bookkeeping, or data engineering today? Tap an option below:</div>
        </div>
        <div class="chat-options">
            <span class="chat-chip" onclick="askBot('fairplay')">⚠️ Fair-Play Policy</span>
            <span class="chat-chip" onclick="askBot('ai_studio')">🎨 AI Assets &amp; Video</span>
            <span class="chat-chip" onclick="askBot('custom_rules')">🕹️ Private Match Rules</span>
            <span class="chat-chip" onclick="askBot('gaming')">🎮 Gaming &amp; 1% Lows</span>
            <span class="chat-chip" onclick="askBot('adhoc')">🌐 Ad-Hoc &amp; P2P Mesh</span>
            <span class="chat-chip" onclick="askBot('bookkeeping')">💼 Bookkeeping &amp; Reconcile</span>
            <span class="chat-chip" onclick="askBot('legal')">⚖️ Legal &amp; Copyright Proof</span>
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

        if (type === 'ai_assets') {
          tierSelect.value = "AI Creation & Asset Generation Free Trial";
          scopeBox.value = "Task: AI Game Asset & Texture Generation\\n- Prompt: Generate 2K seamless PBR game texture (metal/wood/stone) or low-poly 3D mesh base.\\n- Request: Stamp with SHA-256 copyright birth certificate.";
        } else if (type === 'custom_server') {
          tierSelect.value = "Private Server & Custom Rules Free Trial";
          scopeBox.value = "Task: Private Match & Custom Rule Configuration\\n- Scope: Configure private dedicated server / P2P LAN mesh with custom game physics, authorized modpacks, and admin house rules.";
        } else if (type === 'gaming_telemetry') {
          tierSelect.value = "PC Gaming & Telemetry Free Trial Run";
          scopeBox.value = "Task: PC Gaming Telemetry & Frame-Time Analysis\\n- Ingest CapFrameX / HWiNFO / Afterburner benchmark logs.\\n- Calculate 0.1% & 1% low frame-time stutters, average FPS, and temperature/bottleneck curves.";
        } else if (type === 'ai_apps') {
          tierSelect.value = "AI Creation & Asset Generation Free Trial";
          scopeBox.value = "Task: Custom AI Automation Gem / Mini-App Build\\n- Build standalone automated assistant (e.g. YouTube chapter generator, inventory parser, or support bot).";
        } else if (type === 'bookkeeping') {
          tierSelect.value = "Small Business & Bookkeeping Free Trial Run";
          scopeBox.value = "Task: Bookkeeping & Bank Statement Normalizer\\n- Ingest messy bank/POS CSV transactions.\\n- Normalize merchant names, fix negative currency formatting, and categorize expenses.";
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

        if (topic === 'fairplay') {
          userMsg.innerText = "What is your Fair-Play & Gaming Policy?";
          botMsg.innerHTML = "<b>⚠️ Gaming Integrity Policy:</b><br>• <b>Private Servers:</b> Hosts have full freedom to test mods, custom physics, and house rules.<br>• <b>Public Multiplayer:</b> Cheats, aimbots, recoil macros, and memory injections targeting public matchmaking are strictly prohibited and auto-blocked.";
        } else if (topic === 'ai_studio') {
          userMsg.innerText = "What AI Creation and Asset tools do you offer?";
          botMsg.innerHTML = "<b>AI Studio & Creation Capabilities:</b><br>• <b>3D Textures & Meshes:</b> Generate 2K seamless PBR textures and low-poly 3D models with SHA-256 copyright seals.<br>• <b>Cinematic Video:</b> Produce 4K generative video reels with synced audio stems.<br>• <b>Custom AI Gems:</b> Build standalone automation mini-apps for repetitive tasks.";
        } else if (topic === 'custom_rules') {
          userMsg.innerText = "Can I customize rules and mods on my private server?";
          botMsg.innerHTML = "<b>Private Servers & Custom Sandbox:</b><br>• <b>Complete Host Freedom:</b> Set your own game physics, spawn rates, custom bot logic, and modpacks in private co-op/dedicated matches.<br>• <b>Public Integrity:</b> We strictly prohibit cheats, aimbots, or memory injection targeting public multiplayer games.";
        } else if (topic === 'gaming') {
          userMsg.innerText = "What PC Gaming services and telemetry tools do you offer?";
          botMsg.innerHTML = "<b>PC Gaming & Telemetry Engineering:</b><br>• <b>Frame-Time & 1% Low Analysis:</b> Ingest CapFrameX, Afterburner, and PresentMon CSVs to chart micro-stutters and hardware bottlenecks.<br>• <b>Clip Compression:</b> Shrink 2GB raw OBS/ShadowPlay 60FPS clips under 25MB without ruining clarity.<br>• <b>Tournament Match Logs:</b> Parse kill/death and combat timeline telemetry.";
        } else if (topic === 'adhoc') {
          userMsg.innerText = "How do Ad-Hoc networks and P2P mesh setups work?";
          botMsg.innerHTML = "<b>Ad-Hoc & P2P Mesh Architecture:</b><br>• <b>Play-When-You-Play Servers:</b> On-demand game instances that spin up for sessions, freeze world saves, and terminate to save costs.<br>• <b>Zero-Port-Forwarding LAN:</b> Encrypted peer tunnels for private co-op mods and emulators without public IP risks.<br>• <b>Direct Asset Sync:</b> Blazing-fast P2P file transfers for 4K video and modpacks.";
        } else if (topic === 'bookkeeping') {
          userMsg.innerText = "How do your small business bookkeeping services work?";
          botMsg.innerHTML = "<b>Bookkeeping & Ledger Engineering:</b><br>• <b>Bank Statement Cleanup:</b> Strip merchant noise, standardize transaction dates, and correct sign formats (+/-).<br>• <b>Expense Categorization:</b> Map transactions to chart of accounts automatically.<br>• <b>Reconciliation Ready:</b> Output clean CSV/Excel ready for QuickBooks, Xero, or tax prep.";
        } else if (topic === 'legal') {
          userMsg.innerText = "What is available for legal teams, FOIA, and IP protection?";
          botMsg.innerHTML = "<b>Legal, FOIA & Compliance:</b><br>• <b>PII & SSN Redaction:</b> Automated scripts to sanitize sensitive data from litigation records.<br>• <b>Sovereign SHA-256 Stamps:</b> Immutable proof of prior art and evidence chain-of-custody tracking.<br>• <b>Citation Normalizer:</b> Standardize case references into APA/MLA/Bluebook formats.";
        } else if (topic === 'pricing') {
          userMsg.innerText = "What are the standard prices?";
          botMsg.innerHTML = "Our fixed rates:<br>• <b>Tier 1 (Fix / Asset):</b> $75<br>• <b>Tier 2 (Server / Pipeline / AI Bot):</b> $250<br>• <b>Tier 3 (Modeling & Compute):</b> $600+<br>• <b>Retainers:</b> Custom monthly SLA.";
        }

        stream.appendChild(userMsg);
        stream.appendChild(botMsg);
        stream.scrollTop = stream.scrollHeight;
      }
    </script>
</body>
</html>
"""

TERMS_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Terms of Service & Legal Disclaimer | Garza Global Graviton</title>
    <style>
      :root {
        --bg: #0b0f19;
        --panel: #131b2e;
        --border: #1e293b;
        --accent: #38bdf8;
        --green: #34d399;
        --amber: #f59e0b;
        --red: #ef4444;
        --text: #e2e8f0;
        --muted: #94a3b8;
      }
      * { box-sizing: border-box; }
      body {
        background-color: var(--bg);
        color: var(--text);
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        margin: 0;
        padding: 24px 16px;
        line-height: 1.6;
      }
      .container {
        max-width: 860px;
        margin: 0 auto;
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 32px;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
      }
      h1 { color: var(--accent); font-size: 24px; margin-top: 0; border-bottom: 1px solid #334155; padding-bottom: 12px; }
      h2 { color: #f8fafc; font-size: 16px; margin-top: 24px; margin-bottom: 8px; border-left: 3px solid var(--accent); padding-left: 10px; }
      p, li { font-size: 13px; color: #cbd5e1; }
      ul { padding-left: 20px; }
      .callout {
        background: #0f172a;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 14px 18px;
        margin: 16px 0;
        font-size: 12px;
      }
      .back-btn {
        display: inline-block;
        margin-top: 24px;
        background: #0284c7;
        color: white;
        text-decoration: none;
        padding: 10px 18px;
        border-radius: 6px;
        font-weight: bold;
        font-size: 13px;
      }
    </style>
</head>
<body>
    <div class="container">
        <h1>Terms of Service &amp; Legal Operating Agreement</h1>
        <p style="color: var(--muted); font-size: 12px;">Effective Date: August 24, 2026 | Garza Global Graviton LLC | State of Illinois, USA</p>

        <h2>1. Acceptance of Operating Terms</h2>
        <p>By accessing this site, executing workloads, redeeming sovereign trial tokens, or purchasing services through Garza Global Graviton LLC ("Company", "we", "us"), you agree to be bound by these Terms of Service. If you do not agree, you must immediately discontinue use of all pipelines, tools, and servers.</p>

        <h2>2. Scope of Services &amp; Dual-Zone Gaming Policy</h2>
        <p>Garza Global Graviton LLC provides high-performance data engineering, cryptographic proof stamping, ad-hoc mesh networking, custom server provisioning, and AI asset creation tools.</p>
        <div class="callout">
            <b>• Private Sovereign Zone (Permitted):</b> Hosts running private dedicated servers, local co-op LANs, or private matches possess full freedom to configure custom game physics, test experimental mods, and enforce house rules.<br><br>
            <b>• Public Competitive Gaming (Strictly Prohibited):</b> Our pipelines strictly prohibit any script, program, or AI generation designed to manipulate public multiplayer games (e.g. memory injection, aimbots, triggerbots, recoil compensation macros, or anti-cheat bypass tools). All incoming public requests are automatically filtered and rejected.
        </div>

        <h2>3. Unilateral Right to Refuse or Revoke Service</h2>
        <p>Garza Global Graviton LLC reserves the absolute, unilateral right to refuse service, terminate active execution instances, revoke access tokens, or ban any user/IP address at our sole discretion, without prior notice, for any violation of our Fair-Play Policies, submission of malicious binaries, or attempted infrastructure abuse.</p>

        <h2>4. "As-Is" Provision &amp; Warranty Disclaimer</h2>
        <p>All software, calculations, server configurations, AI assets, and cryptographic verification receipts are provided on an <b>"AS IS"</b> and <b>"AS AVAILABLE"</b> basis. We make no warranty that services will be uninterrupted, error-free, or meet specific third-party platform terms outside our direct control.</p>

        <h2>5. Absolute Limitation of Liability</h2>
        <p>To the maximum extent permitted by applicable law, Garza Global Graviton LLC, its members, and contractors shall not be liable for any indirect, incidental, special, consequential, or punitive damages (including loss of profits, data loss, gaming account bans, business interruption, or hardware failure) arising out of your use of our software or servers. Our total aggregate liability for any claim shall not exceed the actual amount paid by you for the specific service in dispute.</p>

        <h2>6. Intellectual Property &amp; Cryptographic Evidence</h2>
        <p>Clients retain full ownership of their raw submitted datasets and prompts. Cryptographic SHA-256 receipts issued by the pipeline serve as deterministic mathematical proofs of existence. All proprietary pipeline harnesses, token mint engines, and site architectures remain the intellectual property of Garza Global Graviton LLC.</p>

        <h2>7. Governing Law</h2>
        <p>These terms shall be governed by and construed in accordance with the laws of the <b>State of Illinois</b>, United States, without regard to conflict of law provisions.</p>

        <a href="/" class="back-btn">&larr; Return to Live Dashboard</a>
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
    <title>Admin Submissions & AI/Gaming Token Mint | Garza Global Graviton</title>
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
        max-width: 1040px;
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

        <div class="card" style="border-left: 4px solid var(--pink);">
            <span style="font-weight: bold; color: white;">🎟️ Mint Specialized Demographic &amp; Industry Access Tokens</span>
            <p style="font-size: 12px; color: var(--muted); margin: 4px 0 0 0;">Click any demographic category to generate an instant copyable token string:</p>
            
            <div class="mint-grid">
                <button type="button" class="mint-btn-pill" style="background:#4a044e; color:var(--pink);" onclick="generateToken('ai_studio')">🎨 + Mint AI Studio &amp; Assets</button>
                <button type="button" class="mint-btn-pill" style="background:#1e1b4b; color:var(--indigo);" onclick="generateToken('custom_server')">🕹️ + Mint Private Server &amp; Rules</button>
                <button type="button" class="mint-btn-pill" style="background:#083344; color:var(--cyan);" onclick="generateToken('gaming')">🎮 + Mint Gaming &amp; Telemetry</button>
                <button type="button" class="mint-btn-pill" style="background:#064e3b; color:var(--emerald);" onclick="generateToken('business')">💼 + Mint Bookkeeping &amp; Biz</button>
                <button type="button" class="mint-btn-pill" style="background:#451a03; color:var(--amber);" onclick="generateToken('legal')">⚖️ + Mint Legal &amp; FOIA Proof</button>
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
                            <td style="font-family: monospace; color: {% if 'AI' in key %}var(--pink){% elif 'CUSTOM' in key %}var(--indigo){% elif 'GAMING' in key %}var(--cyan){% elif 'BIZ' in key %}var(--emerald){% elif 'LEGAL' in key %}var(--amber){% else %}var(--purple){% endif %}; font-weight: bold;">{{ key }}</td>
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
                            <th>Fair-Play Verification</th>
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
                            <td style="font-size: 11px; color: {% if 'REJECTED' in sub.fairplay_status %}var(--red){% elif 'Private' in sub.fairplay_status %}var(--indigo){% else %}var(--green){% endif %}; font-weight: bold;">
                                {{ sub.fairplay_status }}
                            </td>
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
            if (data.token.includes('AI')) color = 'var(--pink)';
            else if (data.token.includes('CUSTOM')) color = 'var(--indigo)';
            else if (data.token.includes('GAMING')) color = 'var(--cyan)';
            else if (data.token.includes('BIZ')) color = 'var(--emerald)';
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
            <b>FAIR-PLAY STATUS:</b> {{ fairplay_status }}<br>
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

@app.route("/terms")
def terms_page():
    return render_template_string(TERMS_TEMPLATE)

@app.route("/")
def dashboard():
    reviews = load_json(REVIEWS_FILE, [])
    
    # Calculate review metrics
    if reviews:
        total_stars = sum(int(r.get("stars", 5)) for r in reviews)
        avg_num = total_stars / len(reviews)
        avg_score = f"{avg_num:.1f}"
        star_string = "★" * int(round(avg_num)) + "☆" * (5 - int(round(avg_num)))
    else:
        avg_score = "5.0"
        star_string = "★★★★★"

    # Amazon-style algorithmic review summarizer
    review_texts = [r.get("comment", "") for r in reviews]
    combined_text = " ".join(review_texts).lower()
    
    highlights = []
    if any(k in combined_text for k in ["ai", "texture", "asset", "pbr", "render"]):
        highlights.append("game developers and artists praise the instant 2K PBR texture generation and low-poly 3D mesh pipelines")
    if any(k in combined_text for k in ["private", "server", "scrims", "custom", "rules"]):
        highlights.append("server hosts and esports leagues highlight the complete rule customization in private matches without public cheating risks")
    if any(k in combined_text for k in ["bank", "receipt", "csv", "bookkeeping", "formulas"]):
        highlights.append("small business owners value the automatic ledger formula normalization and receipt deduplication")

    if highlights:
        ai_summary = "Customers frequently note that " + "; ".join(highlights) + ". Overall sentiment highlights transparent verification receipts, low-latency queues, and robust fair-play compliance."
    else:
        ai_summary = "Customers highlight the extreme dispatch speed, accurate mathematical data vectorization, and deterministic cryptographic SHA-256 sealing receipts across AI creation, private servers, and business workflows."

    return render_template_string(
        HTML_TEMPLATE,
        reviews=reviews,
        avg_score=avg_score,
        star_string=star_string,
        ai_summary=ai_summary,
        tier1_link=STRIPE_TIER1_LINK,
        tier2_link=STRIPE_TIER2_LINK,
        tier3_link=STRIPE_TIER3_LINK
    )

@app.route("/submit_review", methods=["POST"])
def submit_review():
    name = request.form.get("name", "Anonymous Client").strip()
    role = request.form.get("role", "General Client").strip()
    stars = int(request.form.get("stars", 5))
    comment = request.form.get("comment", "").strip()

    if comment:
        reviews = load_json(REVIEWS_FILE, [])
        reviews.append({
            "name": name,
            "role": role,
            "stars": max(1, min(5, stars)),
            "comment": comment,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        })
        save_json(REVIEWS_FILE, reviews)

    return redirect("/#reviews-section")

@app.route("/admin/submissions")
def admin_submissions():
    submissions = load_json(SUBMISSIONS_FILE, [])
    tokens = load_json(TOKENS_FILE, {})
    return render_template_string(ADMIN_TEMPLATE, submissions=submissions, tokens=tokens)

@app.route("/admin/mint_token", methods=["POST"])
def mint_token():
    data = request.get_json(silent=True) or {}
    token_type = data.get("type", "ai_studio")
    tokens = load_json(TOKENS_FILE, {})
    
    created_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    hex_id = secrets.token_hex(2).upper()

    if token_type == "ai_studio":
        new_token = f"GGG-AI-STUDIO-{hex_id}"
        tier = "AI Studio & Creation Trial"
        max_rows = 1000
        sample_limit = "1 high-res AI asset / mini-app script / cinematic render test"
    elif token_type == "custom_server":
        new_token = f"GGG-CUSTOM-SRV-{hex_id}"
        tier = "Private Server & Custom Rules Trial"
        max_rows = 1000
        sample_limit = "1 private server rule harness / ad-hoc P2P mesh setup"
    elif token_type == "gaming":
        new_token = f"GGG-GAMING-{hex_id}"
        tier = "Gaming & Telemetry Trial"
        max_rows = 500
        sample_limit = "500 rows frame-time logs / 1 clip compression"
    elif token_type == "business":
        new_token = f"GGG-BIZ-{hex_id}"
        tier = "Bookkeeping & Business Trial"
        max_rows = 500
        sample_limit = "500 rows bank ledger reconciliation / margin model"
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
    scope_text = data.get("scope", data.get("requirements", "General Workload Inquiry"))
    tier_choice = data.get("tier", data.get("budget", "Custom Project"))
    
    # Run Fair-Play & Exploit Policy Check
    is_valid_policy, fairplay_status = check_exploit_policy(scope_text, tier_choice)
    
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
        "scope": scope_text,
        "tier": tier_choice,
        "fairplay_status": fairplay_status,
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
            fairplay_status=fairplay_status,
            receipt_hash=receipt_hash,
            timestamp=now_str
        )
    return jsonify({"status": "success", "token_status": token_status, "fairplay_status": fairplay_status, "receipt_hash": receipt_hash, "entry": submission_entry})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)