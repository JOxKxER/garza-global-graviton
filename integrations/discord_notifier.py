"""
integrations/discord_notifier.py - Real-Time Discord Alert Relay
Sends critical system alerts and task notifications to a Discord channel via Webhook.
"""

import requests
import db_manager as db

def send_discord_alert(title, message, color=16711680):
    """Fetches the webhook URL from database policies and posts an alert embed."""
    policies = db.get_policies()
    webhook_url = policies.get("discord_webhook_url", "")
    
    if not webhook_url:
        print("ℹ️ Discord Webhook URL not configured in database policies.")
        return False

    payload = {
        "embeds": [{
            "title": f"⚡ GGG Alert: {title}",
            "description": message,
            "color": color,
            "footer": {"text": "Garza Global Graviton Autonomous Watchdog"}
        }]
    }
    
    try:
        response = requests.post(webhook_url, json=payload)
        if response.status_code == 204:
            print("✅ Discord alert successfully dispatched.")
            return True
        else:
            print(f"⚠️ Discord webhook failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error sending Discord alert: {e}")
        return False