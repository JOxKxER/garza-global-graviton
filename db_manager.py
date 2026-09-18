import sqlite3
import os

DB_PATH = "V:\\03_Source_Code\\data_in\\mesh_telemetry.db"

def init_database():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Enable Write-Ahead Logging for high-concurrency performance
    cursor.execute("PRAGMA journal_mode=WAL;")
    
    # Create telemetry and node communication tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS node_telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            metric_key TEXT NOT NULL,
            metric_value REAL NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mesh_messages (
            message_id TEXT PRIMARY KEY,
            sender TEXT NOT NULL,
            receiver TEXT NOT NULL,
            payload TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    print("Database initialized successfully with WAL mode.")

if __name__ == "__main__":
    init_database()