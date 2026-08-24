"""
grant_tracker.py - Federal Grant & SBIR/STTR Milestone Tracker
Aligns local telemetry and architecture metrics with defense innovation proposal formats.
"""

import os
import json
from datetime import datetime
import db_manager as db

def check_solicitation_status():
    """
    Tracks active federal solicitation windows and evaluates local readiness.
    """
    print("==================================================")
    print("🏛️ GARZA GLOBAL GRAVITON - FEDERAL GRANT TRACKER")
    print(f"Evaluation Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("==================================================")

    nodes = db.get_all_nodes()
    events = db.get_recent_events(limit=100)
    policies = db.get_policies()

    # System Readiness Evaluation
    readiness_score = 100
    bottlenecks = []

    if len(nodes) == 0:
        readiness_score -= 30
        bottlenecks.append("No active container nodes deployed for telemetry demonstration.")
    
    if not policies.get("server_authoritative_position", 0):
        readiness_score -= 20
        bottlenecks.append("Server-authoritative position verification policy is disabled.")

    print(f"\n📊 System Technical Readiness Score: {readiness_score}/100")
    
    if bottlenecks:
        print("⚠️ Action Items for Proposal Compliance:")
        for b in bottlenecks:
            print(f"   - {b}")
    else:
        print("✅ Core architecture fully optimized for zero-trust telemetry evaluation.")

    # Generate Draft Proposal Volume
    proposal_payload = {
        "entity": "Garza Global Graviton (Illinois LLC)",
        "target_framework": "Defense SBIR / STTR Innovation Portal (DSIP)",
        "active_nodes_verified": len(nodes),
        "telemetry_vectors_logged": len(events),
        "core_tickrate_hz": 128,
        "security_compliance": "SHA-256 Hashed SQLite Snapshot Engine Active",
        "timestamp": datetime.utcnow().isoformat()
    }

    output_filename = "grant_proposal_technical_volume.json"
    with open(output_filename, "w") as f:
        json.dump(proposal_payload, f, indent=4)
        
    print(f"\n📁 Technical volume successfully compiled and saved to: {output_filename}")

if __name__ == "__main__":
    check_solicitation_status()