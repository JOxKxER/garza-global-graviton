"""
fix_tokens_table.py - Recreates the user_tokens table with the correct schema
"""

import sqlite3

def fix_tokens():
    conn = sqlite3.connect("vault_storage.db")
    cursor = conn.cursor()
    
    # Drop old malformed table if it exists
    cursor.execute("DROP TABLE IF EXISTS user_tokens")
    
    # Recreate table with correct schema
    cursor.execute("""
        CREATE TABLE user_tokens (
            username TEXT PRIMARY KEY,
            balance INTEGER
        )
    """)
    
    conn.commit()
    conn.close()
    print("✅ user_tokens table successfully rebuilt with the 'balance' column!")

if __name__ == "__main__":
    fix_tokens()