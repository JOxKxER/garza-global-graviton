"""
setup_discord.py - Interactive Discord Webhook Configuration
Saves your private Discord channel webhook URL into the vault database policies table.
"""

import sqlite3

def configure_webhook():
    print("=== Garza Global Graviton - Discord Webhook Setup ===")
    url = input("Enter your Discord Webhook URL: ").strip()
    
    if not url.startswith("https://discord.com/api/webhooks/"):
        print("⚠️ Warning: That doesn't look like a standard Discord webhook URL, but saving anyway...")

    conn = sqlite3.connect("vault_storage.db")
    conn.execute("INSERT OR REPLACE INTO policies (key, value) VALUES ('discord_webhook_url', ?)", (url,))
    conn.commit()
    conn.close()
    print("✅ Discord Webhook URL successfully saved to vault database!")

if __name__ == "__main__":
    configure_webhook()