"""
migrate_to_sqlite.py - JSON to SQLite Database Migration Engine
Creates vault.db schema and imports existing configuration, users,
mesh devices, tournament records, and security events.
Run with: python migrate_to_sqlite.py
"""

import sqlite3
import json
import os
import sys

DB_FILE = "vault.db"
CONFIG_FILE = "config.json"
EVENTS_LOG_FILE = "security_events.json"

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_schema(cursor):
    """Initializes normalized database tables and indexes."""
    cursor.executescript("""
    -- System Integrity Policies
    CREATE TABLE IF NOT EXISTS integrity_policies (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        server_authoritative_position BOOLEAN NOT NULL DEFAULT 1,
        sub_tick_packet_scan BOOLEAN NOT NULL DEFAULT 1,
        auto_kick_memory_hook BOOLEAN NOT NULL DEFAULT 1,
        velocity_deviation_sigma REAL NOT NULL DEFAULT 2.2,
        aim_vector_threshold_deg_per_ms REAL NOT NULL DEFAULT 65.0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- User Profiles & Billing
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        gamer_tag TEXT NOT NULL,
        email TEXT NOT NULL,
        role TEXT DEFAULT 'Squad Leader',
        age_verified BOOLEAN DEFAULT 0,
        parent_guardian_name TEXT DEFAULT 'N/A',
        card_brand TEXT,
        card_last4 TEXT,
        card_exp TEXT,
        token_balance INTEGER DEFAULT 150,
        referral_code TEXT UNIQUE,
        referred_users TEXT DEFAULT '[]', -- JSON Array
        active_addons TEXT DEFAULT '[]',   -- JSON Array
        linked_accounts TEXT DEFAULT '{}', -- JSON Object (Discord, Twitch, Steam)
        matches_played INTEGER DEFAULT 0,
        clean_reputation_score INTEGER DEFAULT 100,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Dedicated Server Fleet Nodes
    CREATE TABLE IF NOT EXISTS active_nodes (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        region TEXT NOT NULL,
        plan TEXT NOT NULL,
        admin_email TEXT NOT NULL,
        tickrate INTEGER DEFAULT 128,
        status TEXT DEFAULT 'Online',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Public Matchmaking Lobbies
    CREATE TABLE IF NOT EXISTS public_lobbies (
        lobby_id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        host_tag TEXT NOT NULL,
        twitch_stream TEXT,
        region TEXT NOT NULL,
        mode TEXT NOT NULL,
        max_slots INTEGER DEFAULT 8,
        players TEXT NOT NULL DEFAULT '[]', -- JSON Array
        auto_fill BOOLEAN DEFAULT 1,
        min_rep INTEGER DEFAULT 90,
        server_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Paired Hardware Mesh Fleet
    CREATE TABLE IF NOT EXISTS device_mesh (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        fingerprint TEXT NOT NULL,
        status TEXT DEFAULT 'Paired / Encrypted',
        last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Compressed Replay & Telemetry Archives
    CREATE TABLE IF NOT EXISTS stored_replays (
        id TEXT PRIMARY KEY,
        match_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        raw_bytes INTEGER,
        compressed_bytes INTEGER,
        compression_ratio TEXT,
        status TEXT
    );

    -- Tournament Records & Cryptographic Merkle Receipts
    CREATE TABLE IF NOT EXISTS tournament_records (
        match_id TEXT PRIMARY KEY,
        server_id TEXT,
        finalized_at TEXT,
        tickrate_hz INTEGER,
        total_ticks_analyzed INTEGER,
        winner_team TEXT,
        fair_play_certified BOOLEAN,
        merkle_root TEXT NOT NULL,
        roster TEXT,              -- JSON Array
        receipt_json TEXT NOT NULL -- Full JSON receipt string
    );

    -- Real-Time Security Event Stream
    CREATE TABLE IF NOT EXISTS security_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        node_id TEXT,
        node_name TEXT,
        vector TEXT NOT NULL,
        action_taken TEXT NOT NULL,
        confidence TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_events_timestamp ON security_events(timestamp DESC);
    CREATE INDEX IF NOT EXISTS idx_users_gamer_tag ON users(gamer_tag);
    """)

def migrate_config(cursor):
    """Imports data from config.json into relational tables."""
    if not os.path.exists(CONFIG_FILE):
        print(f"[WARN] {CONFIG_FILE} not found. Skipping config migration.")
        return

    with open(CONFIG_FILE, "r") as f:
        try:
            cfg = json.load(f)
        except Exception as e:
            print(f"[ERROR] Failed to parse {CONFIG_FILE}: {e}")
            return

    # 1. Integrity Policies
    policies = cfg.get("integrity_policies", {})
    cursor.execute("""
    INSERT OR REPLACE INTO integrity_policies 
    (id, server_authoritative_position, sub_tick_packet_scan, auto_kick_memory_hook, velocity_deviation_sigma, aim_vector_threshold_deg_per_ms)
    VALUES (1, ?, ?, ?, ?, ?)
    """, (
        policies.get("server_authoritative_position", True),
        policies.get("sub_tick_packet_scan", True),
        policies.get("auto_kick_memory_hook", True),
        policies.get("velocity_deviation_sigma", 2.2),
        policies.get("aim_vector_threshold_deg_per_ms", 65.0)
    ))

    # 2. Users
    users = cfg.get("users", [])
    for u in users:
        card = u.get("saved_card") or {}
        cursor.execute("""
        INSERT OR REPLACE INTO users 
        (username, gamer_tag, email, role, age_verified, parent_guardian_name, card_brand, card_last4, card_exp,
         token_balance, referral_code, referred_users, active_addons, linked_accounts, matches_played, clean_reputation_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            u.get("username"),
            u.get("gamer_tag", "Gamer#0001"),
            u.get("email", ""),
            u.get("role", "Squad Leader"),
            u.get("age_verified", False),
            u.get("parent_guardian_name", "N/A"),
            card.get("brand"),
            card.get("last4"),
            card.get("exp"),
            u.get("token_balance", 150),
            u.get("referral_code", f"{u.get('username', 'USER').upper()[:4]}-1001"),
            json.dumps(u.get("referred_users", [])),
            json.dumps(u.get("active_addons", [])),
            json.dumps(u.get("linked_accounts", {})),
            u.get("matches_played", 0),
            u.get("clean_reputation_score", 100)
        ))

    # 3. Active Dedicated Server Nodes
    for node in cfg.get("active_nodes", []):
        cursor.execute("""
        INSERT OR REPLACE INTO active_nodes 
        (id, name, region, plan, admin_email, tickrate, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            node.get("id"),
            node.get("name"),
            node.get("region"),
            node.get("plan"),
            node.get("admin_email"),
            node.get("tickrate", 128),
            node.get("status", "Online"),
            node.get("created_at")
        ))

    # 4. Public Lobbies
    for lobby in cfg.get("public_lobbies", []):
        cursor.execute("""
        INSERT OR REPLACE INTO public_lobbies
        (lobby_id, title, host_tag, twitch_stream, region, mode, max_slots, players, auto_fill, min_rep, server_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            lobby.get("lobby_id"),
            lobby.get("title"),
            lobby.get("host_tag"),
            lobby.get("twitch_stream", ""),
            lobby.get("region"),
            lobby.get("mode"),
            lobby.get("max_slots", 8),
            json.dumps(lobby.get("players", [])),
            lobby.get("auto_fill", True),
            lobby.get("min_rep", 90),
            lobby.get("server_id", "node-us-01")
        ))

    # 5. Device Mesh
    for dev in cfg.get("device_mesh", []):
        cursor.execute("""
        INSERT OR REPLACE INTO device_mesh
        (id, name, type, fingerprint, status, last_seen)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            dev.get("id"),
            dev.get("name"),
            dev.get("type"),
            dev.get("fingerprint"),
            dev.get("status", "Paired / Encrypted"),
            dev.get("last_seen")
        ))

    # 6. Tournament Records
    for tr in cfg.get("tournament_records", []):
        match_id = tr.get("match_id", f"match-{os.urandom(4).hex()}")
        crypto = tr.get("cryptography", {})
        outcome = tr.get("match_outcome", {})
        cursor.execute("""
        INSERT OR REPLACE INTO tournament_records
        (match_id, server_id, finalized_at, tickrate_hz, total_ticks_analyzed, winner_team, fair_play_certified, merkle_root, roster, receipt_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            match_id,
            tr.get("server_id"),
            tr.get("finalized_at"),
            tr.get("tickrate_hz", 128),
            tr.get("total_ticks_analyzed", 0),
            outcome.get("winner"),
            outcome.get("fair_play_certified", True),
            crypto.get("merkle_root", ""),
            json.dumps(tr.get("roster", [])),
            json.dumps(tr)
        ))

def migrate_security_events(cursor):
    """Imports existing security event logs into the database."""
    if not os.path.exists(EVENTS_LOG_FILE):
        return

    with open(EVENTS_LOG_FILE, "r") as f:
        try:
            events = json.load(f)
        except Exception:
            return

    for ev in events:
        cursor.execute("""
        INSERT INTO security_events (timestamp, node_id, node_name, vector, action_taken, confidence)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            ev.get("timestamp"),
            ev.get("node_id"),
            ev.get("node_name"),
            ev.get("vector"),
            ev.get("action_taken"),
            ev.get("confidence")
        ))

def run_migration():
    print("=" * 65)
    print("🚀 INITIALIZING SQLITE DATABASE MIGRATION -> vault.db")
    print("=" * 65)

    conn = get_connection()
    cursor = conn.cursor()

    try:
        print("[1/3] Generating relational tables and indexes...")
        init_schema(cursor)

        print("[2/3] Migrating config.json (Users, Nodes, Lobbies, Mesh, Records)...")
        migrate_config(cursor)

        print("[3/3] Migrating security_events.json...")
        migrate_security_events(cursor)

        conn.commit()
        print("\n✅ MIGRATION COMPLETED SUCCESSFULLY!")
        
        # Print Summary Verification
        print("\n--- DATABASE AUDIT SUMMARY ---")
        for table in ["users", "active_nodes", "public_lobbies", "device_mesh", "tournament_records", "security_events"]:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f" • Table [{table}]: {count} records loaded")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ [ERROR] Migration failed: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()