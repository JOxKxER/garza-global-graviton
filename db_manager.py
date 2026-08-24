"""
db_manager.py - Centralized SQLite Database Engine & Management Module
Handles persistence for fleet nodes, security events, system alerts, compliance vault, 
stakeholder requests, user tokens, and human data crunch tasks.
"""

import sqlite3
import pandas as pd
from datetime import datetime

DB_NAME = "vault_storage.db"

def init_db():
    """Initializes all database tables if they do not exist."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Nodes Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nodes (
            id TEXT PRIMARY KEY,
            name TEXT,
            region TEXT,
            plan TEXT,
            tickrate REAL,
            status TEXT
        )
    """)
    
    # Security Events Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS security_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            node_id TEXT,
            node_name TEXT,
            vector TEXT,
            action_taken TEXT,
            confidence TEXT
        )
    """)
    
    # System Alerts Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            logged_at TEXT,
            severity TEXT,
            component TEXT,
            message TEXT
        )
    """)

    # Compliance Records Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS compliance_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_title TEXT,
            filing_agency TEXT,
            status TEXT,
            due_date TEXT,
            notes TEXT
        )
    """)

    # Stakeholder Requests Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stakeholder_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT,
            organization TEXT,
            email TEXT,
            purpose TEXT,
            submitted_at TEXT
        )
    """)

    # User Tokens Ledger
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_tokens (
            username TEXT PRIMARY KEY,
            balance INTEGER
        )
    """)

    # Crunch Tasks Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS crunch_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_description TEXT,
            status TEXT,
            assigned_worker TEXT,
            created_at TEXT
        )
    """)

    # Policies Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS policies (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # Advertisers Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS advertisers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT,
            email TEXT,
            copy TEXT,
            url TEXT,
            budget INTEGER,
            nsfw_pass BOOLEAN
        )
    """)

    conn.commit()
    conn.close()

# Initialize on import
init_db()

# --- Nodes & Telemetry ---
def get_all_nodes():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, region, plan, tickrate, status FROM nodes")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "region": r[2], "plan": r[3], "tickrate": r[4], "status": r[5]} for r in rows]

def get_recent_events(limit=50):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, node_name, vector, action_taken, confidence FROM security_events ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [{"timestamp": r[0], "node_name": r[1], "vector": r[2], "action_taken": r[3], "confidence": r[4]} for r in rows]

def get_system_alerts(limit=25):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT logged_at, severity, component, message FROM system_alerts ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [{"logged_at": r[0], "severity": r[1], "component": r[2], "message": r[3]} for r in rows]

def log_security_event(node_id, node_name, vector, action_taken, confidence):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO security_events (timestamp, node_id, node_name, vector, action_taken, confidence) VALUES (?, ?, ?, ?, ?, ?)",
                   (timestamp, node_id, node_name, vector, action_taken, confidence))
    conn.commit()
    conn.close()

# --- Compliance & Stakeholders ---
def get_compliance_records():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT document_title, filing_agency, status, due_date, notes FROM compliance_records")
    rows = cursor.fetchall()
    conn.close()
    return [{"document_title": r[0], "filing_agency": r[1], "status": r[2], "due_date": r[3], "notes": r[4]} for r in rows]

def add_compliance_record(title, agency, status, due_date, notes):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO compliance_records (document_title, filing_agency, status, due_date, notes) VALUES (?, ?, ?, ?, ?)",
                   (title, agency, status, due_date, notes))
    conn.commit()
    conn.close()

def submit_stakeholder_request(name, org, email, purpose):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    submitted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO stakeholder_requests (full_name, organization, email, purpose, submitted_at) VALUES (?, ?, ?, ?, ?)",
                   (name, org, email, purpose, submitted_at))
    conn.commit()
    conn.close()

def log_nda_access(name, org, email, scope):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    submitted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO stakeholder_requests (full_name, organization, email, purpose, submitted_at) VALUES (?, ?, ?, ?, ?)",
                   (name, org, email, f"NDA Access - {scope}", submitted_at))
    conn.commit()
    conn.close()

# --- Policies & Tokens ---
def get_policies():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM policies")
    rows = cursor.fetchall()
    conn.close()
    return {r[0]: r[1] for r in rows}

def get_user_tokens(username):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM user_tokens WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0

def award_user_tokens(username, amount):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    current = get_user_tokens(username)
    new_balance = current + amount
    cursor.execute("INSERT OR REPLACE INTO user_tokens (username, balance) VALUES (?, ?)", (username, new_balance))
    conn.commit()
    conn.close()

# --- Human Data Crunch Tasks ---
def get_crunch_tasks():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, task_description, status, assigned_worker, created_at FROM crunch_tasks")
        rows = cursor.fetchall()
        tasks = []
        for r in rows:
            tasks.append({
                "id": r[0],
                "task_description": r[1],
                "status": r[2],
                "assigned_worker": r[3],
                "created_at": r[4]
            })
        return tasks
    except Exception as e:
        print(f"Error fetching crunch tasks: {e}")
        return []
    finally:
        conn.close()

def create_crunch_task(description, assigned_worker):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO crunch_tasks (task_description, status, assigned_worker, created_at) VALUES (?, ?, ?, ?)",
                   (description, "Pending Verification", assigned_worker, created_at))
    conn.commit()
    conn.close()

# --- Advertisers ---
def register_advertiser(company, email, copy, url, budget, nsfw_pass):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO advertisers (company, email, copy, url, budget, nsfw_pass) VALUES (?, ?, ?, ?, ?, ?)",
                   (company, email, copy, url, budget, nsfw_pass))
    conn.commit()
    conn.close()