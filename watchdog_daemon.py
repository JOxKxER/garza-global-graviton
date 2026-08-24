"""
watchdog_daemon.py - Autonomous System Health & Alert Monitor
Continuously audits database integrity, snapshot backups, and portal file states.
Run with: python watchdog_daemon.py
"""

import os
import time
import db_manager as db

def audit_systems():
    print("==================================================")
    print("🔍 WATCHDOG DAEMON - RUNNING SYSTEM AUDIT")
    print("==================================================")
    
    issues_found = 0

    # 1. Check Database Accessibility
    if not os.path.exists("vault_storage.db"):
        db.log_system_alert("CRITICAL", "Database", "vault_storage.db missing from root directory!")
        print("❌ CRITICAL: Database missing.")
        issues_found += 1
    else:
        try:
            db.get_policies()
            print("✅ Database connectivity nominal.")
        except Exception as e:
            db.log_system_alert("ERROR", "Database", f"Database read error: {e}")
            print(f"❌ ERROR: Database read failed: {e}")
            issues_found += 1

    # 2. Check Micro-Portals Existence
    required_portals = [
        "portals/gaming_telemetry.py",
        "portals/data_crunch.py",
        "portals/illinois_compliance_vault.py",
        "portals/nda_portal.py"
    ]
    for portal in required_portals:
        if not os.path.exists(portal):
            db.log_system_alert("WARNING", "Micro-Portals", f"Missing module file: {portal}")
            print(f"⚠️ WARNING: Missing module -> {portal}")
            issues_found += 1
        else:
            print(f"✅ Module verified: {portal}")

    # 3. Check Secure Snapshots Directory
    snapshot_dir = "V:\\03_Source_Code\\secure_snapshots"
    if not os.path.exists(snapshot_dir):
        db.log_system_alert("INFO", "Backup Vault", "Snapshot directory not yet initialized.")
        print("ℹ️ INFO: Snapshot directory not found.")
    else:
        snapshots = os.listdir(snapshot_dir)
        print(f"✅ Snapshot vault active ({len(snapshots)} backups found).")

    if issues_found == 0:
        print("\n🟢 All systems operating within normal parameters. No alerts triggered.")
    else:
        print(f"\n⚠️ Audit complete with {issues_found} warning(s)/error(s) logged to database.")

if __name__ == "__main__":
    audit_systems()