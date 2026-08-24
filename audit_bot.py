"""
audit_bot.py - Automated Background Audit & Telemetry Watchdog Daemon
Periodically runs system stress tests and relays operational reports directly to Discord.
"""

import time
import sqlite3
import requests
from datetime import datetime
from system_stress_audit import test_efficiency_and_performance, test_security_and_integrity, test_legal_and_compliance

DB_NAME = "vault_storage.db"

def get_discord_webhook():
    """Retrieves the saved Discord webhook URL from the database."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM policies WHERE key = 'discord_webhook_url'")
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception:
        return None

def send_discord_report(report_text):
    """Sends the automated audit report to your Discord channel."""
    webhook_url = get_discord_webhook()
    if not webhook_url:
        print("⚠️ Discord webhook URL not found in database policies.")
        return False
        
    payload = {
        "content": f"🛡️ **Garza Global Graviton - Automated Audit Report**\n```{report_text}```"
    }
    try:
        response = requests.post(webhook_url, json=payload)
        if response.status_code == 204:
            print("✅ Automated audit report successfully pushed to Discord!")
            return True
        else:
            print(f"❌ Failed to push Discord alert. Status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error dispatching webhook: {e}")
        return False

def run_scheduled_audit_loop(interval_seconds=3600):
    """Runs the audit suite periodically (default: every 1 hour)."""
    print(f"🤖 Audit Watchdog Daemon started. Running checks every {interval_seconds} seconds...")
    print("Press Ctrl+C to stop the daemon.\n")
    
    while True:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Executing scheduled system audit...")
        
        eff = test_efficiency_and_performance()
        sec = test_security_and_integrity()
        leg = test_legal_and_compliance()
        
        status_msg = "ALL SYSTEMS NOMINAL & SECURE" if (eff and sec and leg) else "WARNING: REVIEW FLAGGED ITEMS"
        
        report = (
            f"Timestamp: {timestamp}\n"
            f"----------------------------------------\n"
            f"Efficiency Test: {'PASS' if eff else 'FAIL'}\n"
            f"Security Vault: {'PASS' if sec else 'FAIL'}\n"
            f"Legal/Compliance: {'PASS' if leg else 'FAIL'}\n"
            f"Overall Status: {status_msg}"
        )
        
        send_discord_report(report)
        
        print(f"💤 Sleeping for {interval_seconds} seconds...\n")
        time.sleep(interval_seconds)

if __name__ == "__main__":
    # For immediate testing, you can change interval_seconds to 60 (1 minute)
    run_scheduled_audit_loop(interval_seconds=3600)