"""
dsip_exporter.py - Automated Defense SBIR/STTR Proposal Exporter
Bundles telemetry metrics, adaptive policy states, and verification logs into an upload archive.
"""

import os
import json
import zipfile
from datetime import datetime
import db_manager as db

BUNDLE_DIR = "dsip_upload_package"

def export_dsip_package():
    print("==================================================")
    print("📦 PREPARING DSIP PROPOSAL UPLOAD PACKAGE")
    print(f"Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("==================================================")

    os.makedirs(BUNDLE_DIR, exist_ok=True)

    # 1. Gather Platform State Data
    policies = db.get_policies()
    nodes = db.get_all_nodes()
    events = db.get_recent_events(limit=100)
    requests = db.get_stakeholder_requests()

    # 2. Construct Technical Volume Metadata
    technical_volume = {
        "entity": "Garza Global Graviton (Illinois LLC)",
        "solicitation_target": "DoD FY-26 Release 5 (Open Topics / Zero-Trust Telemetry)",
        "compiled_at": datetime.utcnow().isoformat(),
        "active_infrastructure": {
            "total_nodes": len(nodes),
            "fixed_tickrate_hz": 128.0,
            "nodes_fleet": nodes
        },
        "adaptive_defense_policies": policies,
        "security_ledger": {
            "total_events_logged": len(events),
            "integrity_engine": "SHA-256 Hashed SQLite Snapshot Ledger"
        },
        "governance_and_evaluations": {
            "total_stakeholder_requests": len(requests)
        }
    }

    meta_filename = os.path.join(BUNDLE_DIR, "technical_volume_spec.json")
    with open(meta_filename, "w") as f:
        json.dump(technical_volume, f, indent=4)
    print("   - Generated technical_volume_spec.json")

    # 3. Create Submission ZIP Archive
    zip_name = f"Garza_Global_Graviton_DSIP_Release5_{datetime.utcnow().strftime('%Y%m%d')}.zip"
    
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(meta_filename, arcname="technical_volume_spec.json")
        # Include database backup if available
        if os.path.exists("vault_storage.db"):
            zipf.write("vault_storage.db", arcname="vault_storage_snapshot.db")

    print(f"\n✅ Success! Upload package successfully compiled: {zip_name}")
    print("   -> Ready for manual review and attachment on the DSIP portal.")

if __name__ == "__main__":
    export_dsip_package()