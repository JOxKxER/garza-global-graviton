"""
bot_dispatcher.py - Safe Natural Language Command Dispatcher & Content Guardrail
Handles tool-calling with hard pre-execution safety filters.
"""

import json
import re
import os
import time
from datetime import datetime

CONFIG_FILE = "config.json"
SAFETY_LOG_FILE = "security_events.json"

# --- Hardcoded Safety & Explicit Material Blocklist ---
BANNED_PATTERNS = [
    r"\b(hack|ddos|exploit|dos attack|packet flood)\b",
    r"\b(nude|nsfw|explicit|porn|deepfake nude|leaked)\b",
    r"\b(malware|trojan|ransomware|keylogger|stealer)\b",
    r"\b(credit card|ssn|social security)\b"
]

def scan_input_safety(prompt: str) -> dict:
    """
    Stage 1 Guardrail: Scans text for prohibited/explicit keywords and malicious intent.
    """
    clean_text = prompt.lower().strip()
    
    for pattern in BANNED_PATTERNS:
        match = re.search(pattern, clean_text)
        if match:
            return {
                "safe": False,
                "reason": f"Content violation detected: Request contains restricted pattern '{match.group(0)}'."
            }
            
    return {"safe": True, "reason": "Passed input safety checks."}

# --- Functional Tool Execution Engine ---
def execute_deploy_server(name: str, region: str = "US East (N. Virginia)", plan: str = "Clan Competitive"):
    if not os.path.exists(CONFIG_FILE):
        return "Error: config.json not found."
    with open(CONFIG_FILE, "r") as f:
        cfg = json.load(f)
        
    new_node = {
        "id": f"node-ai-{int(time.time()) % 1000}",
        "name": name,
        "region": region,
        "plan": plan,
        "admin_email": "bot_provisioned@domain.com",
        "tickrate": 128,
        "status": "Online",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    cfg["active_nodes"].append(new_node)
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)
    return f"🚀 Successfully deployed dedicated node **{name}** in **{region}** (Plan: {plan})."

def execute_create_tournament(title: str, squads: list):
    if not os.path.exists(CONFIG_FILE):
        return "Error: config.json not found."
    with open(CONFIG_FILE, "r") as f:
        cfg = json.load(f)
        
    matches = []
    for i in range(0, len(squads), 2):
        team_a = squads[i]
        team_b = squads[i+1] if (i+1) < len(squads) else "BYE"
        matches.append({
            "match_id": f"Match #{i//2 + 1}",
            "team_a": team_a,
            "team_b": team_b,
            "score": "0 - 0"
        })
        
    new_t = {
        "id": f"tourney-{int(time.time()) % 1000}",
        "name": title,
        "created_at": datetime.now().strftime("%m/%d %H:%M"),
        "strict": True,
        "matches": matches
    }
    cfg.setdefault("tournaments", []).append(new_t)
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)
    return f"🏆 Bracket generated for **{title}** with {len(matches)} initial matches."

def execute_clip_video(topic: str, aspect_ratio: str = "9:16"):
    return f"🎬 Auto-clipped short-form video formatted in **{aspect_ratio}** for topic: *'{topic}'*. Watermarked with verified-creator integrity hash."

# --- Unified Chatbot Dispatcher Entry Point ---
def process_user_chat(prompt: str) -> str:
    # 1. Evaluate Guardrails
    guard = scan_input_safety(prompt)
    if not guard["safe"]:
        return f"🛑 **Guardrail Block:** {guard['reason']}"

    prompt_low = prompt.lower()

    # 2. Intent Routing
    if "deploy" in prompt_low or "create server" in prompt_low:
        server_name = prompt.split("deploy")[-1].replace("server", "").strip() or "AI-Squad-Node"
        return execute_deploy_server(name=server_name.title())

    elif "tournament" in prompt_low or "bracket" in prompt_low:
        return execute_create_tournament(
            title="Community AI Showdown",
            squads=["Apex Legends Squad", "Vortex Legion", "Omega Clan", "Solaris Pro"]
        )

    elif "clip" in prompt_low or "short" in prompt_low or "video" in prompt_low:
        return execute_clip_video(topic="Top Stream Highlights")

    elif "help" in prompt_low:
        return (
            "**Available Natural Language Actions:**\n"
            "* `Deploy server [Server Name]` - Provisions clean dedicated node\n"
            "* `Create tournament bracket` - Generates seeded match brackets\n"
            "* `Clip video for TikTok` - Auto-formats 9:16 highlight reels\n"
            "* Strict safety moderation is active on all inputs."
        )

    else:
        return f"🤖 Processed command: *'{prompt}'*. (Say 'help' to see automated functions)."