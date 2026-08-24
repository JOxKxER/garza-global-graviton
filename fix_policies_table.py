"""
fix_policies_table.py - Recreates the policies table with the correct schema
"""

import sqlite3

def fix_table():
    conn = sqlite3.connect("vault_storage.db")
    cursor = conn.cursor()
    
    # Drop old malformed table if it exists
    cursor.execute("DROP TABLE IF EXISTS policies")
    
    # Recreate table with correct schema
    cursor.execute("""
        CREATE TABLE policies (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    
    # Insert your Discord webhook URL right away
    webhook_url = "https://discord.com/api/webhooks/1541263402461302815/UH-VerYfrSD5ffE2ohQOMs5qeuxMfcbmUlNhbHu3gLfuh-CDE65AMCWQyh8RbBtNP-ly"
    cursor.execute("INSERT INTO policies (key, value) VALUES ('discord_webhook_url', ?)", (webhook_url,))
    
    conn.commit()
    conn.close()
    print("✅ Policies table successfully rebuilt and Discord webhook saved!")

if __name__ == "__main__":
    fix_table()