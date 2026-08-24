"""
set_webhook_auto.py - Automatically saves your Discord Webhook URL to the database.
"""

import sqlite3

def save_webhook():
    webhook_url = "https://discord.com/api/webhooks/1541263402461302815/UH-VerYfrSD5ffE2ohQOMs5qeuxMfcbmUlNhbHu3gLfuh-CDE65AMCWQyh8RbBtNP-ly"
    
    conn = sqlite3.connect("vault_storage.db")
    conn.execute("INSERT OR REPLACE INTO policies (key, value) VALUES ('discord_webhook_url', ?)", (webhook_url,))
    conn.commit()
    conn.close()
    print("✅ Discord Webhook URL automatically saved to database vault!")

if __name__ == "__main__":
    save_webhook()