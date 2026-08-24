"""
discord_notifier.py - Automated Discord Webhook & Embed Dispatcher
Dispatches cryptographic match receipts, anti-cheat enforcement alerts,
and tournament bracket announcements directly to Discord channels.
"""

import urllib.request
import urllib.parse
import json
from datetime import datetime
from typing import Dict, Any, Optional

def dispatch_discord_embed(webhook_url: str, embed_data: Dict[str, Any]) -> bool:
    """Sends a formatted JSON embed payload to a target Discord webhook URL."""
    if not webhook_url or not webhook_url.startswith("https://discord.com/api/webhooks/"):
        return False

    payload = {
        "username": "Server Vault Sentinel",
        "avatar_url": "https://img.icons8.com/fluency/96/shield.png",
        "embeds": [embed_data]
    }

    try:
        req_data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            webhook_url,
            data=req_data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ServerVault/1.0"
            }
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status in [200, 204]
    except Exception as e:
        print(f"[ERROR] Failed to dispatch Discord webhook: {e}")
        return False

def notify_match_sealed(webhook_url: str, receipt: Dict[str, Any]) -> bool:
    """Dispatches an official match completion and Merkle cryptographic certificate embed."""
    merkle_root = receipt.get("cryptography", {}).get("merkle_root", "UNKNOWN")
    winner = receipt.get("match_outcome", {}).get("winner", "TBD")
    match_id = receipt.get("match_id", "Match")
    ticks = receipt.get("total_ticks_analyzed", 0)
    roster = ", ".join(receipt.get("roster", []))

    embed = {
        "title": f"🏆 Official Match Sealed: {match_id}",
        "description": f"Match concluded and sealed with **SHA-256 Merkle Telemetry Tree**.",
        "color": 0x00FF88,  # Green
        "fields": [
            {"name": "Winning Squad", "value": f"👑 **{winner}**", "inline": True},
            {"name": "Tickrate / Auth Ticks", "value": f"{receipt.get('tickrate_hz', 128)} Hz ({ticks} Ticks)", "inline": True},
            {"name": "Active Roster", "value": roster if roster else "N/A", "inline": False},
            {"name": "Merkle Root Hash (Tamper-Proof)", "value": f"`{merkle_root}`", "inline": False}
        ],
        "footer": {
            "text": "Deterministic Anti-Cheat & Fair-Play Engine",
            "icon_url": "https://img.icons8.com/fluency/48/lock-2.png"
        },
        "timestamp": datetime.utcnow().isoformat()
    }
    return dispatch_discord_embed(webhook_url, embed)

def notify_security_violation(webhook_url: str, alert_event: Dict[str, Any]) -> bool:
    """Dispatches a high-priority red embed alert when an anti-cheat anomaly fires."""
    embed = {
        "title": "🚨 Heuristic Violation Detected",
        "description": f"Anti-cheat engine flagged a policy breach on instance `{alert_event.get('node_name')}`.",
        "color": 0xFF0033,  # Red
        "fields": [
            {"name": "Detection Vector", "value": alert_event.get("vector", "Unknown Vector"), "inline": False},
            {"name": "Action Taken", "value": f"⚡ **{alert_event.get('action_taken')}**", "inline": True},
            {"name": "Confidence Rating", "value": f"🔒 `{alert_event.get('confidence')}`", "inline": True}
        ],
        "footer": {
            "text": f"Server Node: {alert_event.get('node_id')}"
        },
        "timestamp": datetime.utcnow().isoformat()
    }
    return dispatch_discord_embed(webhook_url, embed)