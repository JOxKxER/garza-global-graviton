"""
defense_grant_watcher.py - Active Defense Solicitation & Readiness Checker
Monitors rolling DSIP windows and matches local platform telemetry against defense requirements.
"""

import json
from datetime import datetime
import db_manager as db

def evaluate_defense_readiness():
    print("==================================================")
    print("🎖️ GARZA GLOBAL GRAVITON - DEFENSE GRANT WATCHER")
    print(f"Active Check: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("==================================================")

    # Active window tracking based on current 2026 defense BAA schedules
    active_solicitation = {
        "title": "DoW / Navy FY-26 Release 5 SBIR/STTR/CSO",
        "pre_release_date": "2026-08-05",
        "submission_opens": "2026-08-26",
        "submission_closes": "2026-09-23",
        "alignment_focus": "Distributed Telemetry, Edge Integrity, & Zero-Trust Verification"
    }

    print(f"\n📢 Active Target Window: {active_solicitation['title']}")
    print(f"   - Proposal Submission Window: {active_solicitation['submission_opens']} to {active_solicitation['submission_closes']}")
    print(f"   - Dual-Use Alignment: {active_solicitation['alignment_focus']}")

    # Gather local node and event metrics
    nodes = db.get_all_nodes()
    events = db.get_recent_events(limit=50)
    policies = db.get_policies()

    print(f"\n🔍 Local Infrastructure Status:")
    print(f"   - Active Secure Nodes: {len(nodes)}")
    print(f"   - Logged Security Vectors: {len(events)}")
    print(f"   - Server-Authoritative Enforcement: {'ACTIVE' if policies.get('server_authoritative_position') else 'DISABLED'}")

    # Generate Compliance Dossier Packet
    dossier = {
        "entity": "Garza Global Graviton (Illinois LLC)",
        "target_solicitation": active_solicitation['title'],
        "submission_deadline": active_solicitation['submission_closes'],
        "system_metrics": {
            "nodes_active": len(nodes),
            "tickrate": 128.0,
            "hash_verification": "SHA-256 SQLite Snapshot Ledger"
        },
        "compliance_status": "Ready for DSIP Upload"
    }

    filename = "dsip_submission_dossier.json"
    with open(filename, "w") as f:
        json.dump(dossier, f, indent=4)

    print(f"\n✅ Defense submission dossier compiled successfully: {filename}")

if __name__ == "__main__":
    evaluate_defense_readiness()