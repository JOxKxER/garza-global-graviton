"""
evolution_tracker.py - System Evolution & AI Interaction Audit Ledger
Tracks architectural growth, cryptographic state hashes, and AI collaboration metrics 
for NDA compliance and federal agency review.
"""

import sqlite3
import hashlib
import os
from datetime import datetime

DB_NAME = "vault_storage.db"

def init_evolution_tables():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # System Architecture Evolution Log
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_evolution_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            component_name TEXT,
            change_type TEXT,
            content_hash TEXT,
            auditor_notes TEXT
        )
    """)
    
    # AI Interaction & Collaboration Log
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ai_interaction_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            ai_model TEXT,
            interaction_type TEXT,
            target_module TEXT,
            prompt_context_summary TEXT,
            verification_status TEXT
        )
    """)
    
    conn.commit()
    conn.close()

def log_evolution_event(component_name, change_type, notes):
    """Logs a structural system evolution event with a cryptographic SHA-256 state hash."""
    init_evolution_tables()
    
    file_hash = "N/A"
    if os.path.exists(component_name):
        hasher = hashlib.sha256()
        with open(component_name, "rb") as f:
            hasher.update(f.read())
        file_hash = hasher.hexdigest()[:16]

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute("""
        INSERT INTO system_evolution_log (timestamp, component_name, change_type, content_hash, auditor_notes)
        VALUES (?, ?, ?, ?, ?)
    """, (timestamp, component_name, change_type, file_hash, notes))
    
    conn.commit()
    conn.close()
    print(f"🔒 Evolution Logged: [{component_name}] -> {change_type} (Hash: {file_hash})")

def log_ai_interaction(ai_model, interaction_type, target_module, summary, status="Verified"):
    """Logs how AI models collaborate with the local codebase (e.g., code generation, data crunch oversight)."""
    init_evolution_tables()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute("""
        INSERT INTO ai_interaction_log (timestamp, ai_model, interaction_type, target_module, prompt_context_summary, verification_status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (timestamp, ai_model, interaction_type, target_module, summary, status))
    
    conn.commit()
    conn.close()
    print(f"🤖 AI Interaction Recorded: [{ai_model}] {interaction_type} on {target_module}")

def export_full_audit_trail():
    """Exports a complete report of system growth and AI interactions for NDA reviewers."""
    init_evolution_tables()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    print("\n" + "="*60)
    print("   GARZA GLOBAL GRAVITON: COMPREHENSIVE AUDIT TRAIL       ")
    print("="*60)
    
    print("\n--- 🏗️ SYSTEM ARCHITECTURE EVOLUTION ---")
    cursor.execute("SELECT timestamp, component_name, change_type, content_hash, auditor_notes FROM system_evolution_log")
    for r in cursor.fetchall():
        print(f"[{r[0]}] {r[1]} | Type: {r[2]} | Hash: {r[3]}")
        print(f"  └─ Notes: {r[4]}")
    
    print("\n--- 🤖 AI COLLABORATION & OVERSIGHT LOG ---")
    cursor.execute("SELECT timestamp, ai_model, interaction_type, target_module, prompt_context_summary, verification_status FROM ai_interaction_log")
    for r in cursor.fetchall():
        print(f"[{r[0]}] Model: {r[1]} | Action: {r[2]} | Target: {r[3]}")
        print(f"  └─ Context: {r[4]}")
        print(f"  └─ Status: {r[5]}")
        
    conn.close()
    print("="*60)

if __name__ == "__main__":
    # Record baseline state and AI interaction examples
    log_evolution_event("human_data_crunch.py", "CORE_FEATURE_ADD", "Deployed decentralized human-in-the-loop task engine.")
    log_ai_interaction("Gemini Pro / Local LLM", "CODE_GENERATION", "human_data_crunch.py", "Generated asynchronous task queue logic and database wrappers.", "Human Verified")
    log_ai_interaction("Gemini Pro", "DATA_OVERSIGHT", "vault_storage.db", "Evaluated telemetry anomaly detection and token distribution weights.", "Approved")
    
    export_full_audit_trail()