"""
compile_grant_package.py - Automated SBIR/STTR Grant Package Compiler
Bundles telemetry metrics, database backups, and compliance logs into a submission archive.
"""

import os
import zipfile
import json
from datetime import datetime
import db_manager as db
import backup_manager as backup

PACKAGE_DIR = "grant_submission_bundle"

def build_submission_package():
    print("📦 Compiling Garza Global Graviton Grant Package...")
    os.makedirs(PACKAGE_DIR, exist_ok=True)
    
    # 1. Generate fresh secure database backup and hash
    backup_path = backup.create_secure_backup()
    
    # 2. Gather system metadata and logs
    nodes = db.get_all_nodes()
    events = db.get_recent_events(limit=500)
    policies = db.get_policies()
    
    metadata = {
        "entity": "Garza Global Graviton (Illinois LLC)",
        "target_portal": "Defense SBIR / STTR Innovation Portal",
        "compiled_at": datetime.utcnow().isoformat(),
        "total_active_nodes": len(nodes),
        "total_security_events_logged": len(events),
        "enforced_policies": policies,
        "nodes": nodes
    }
    
    meta_file = os.path.join(PACKAGE_DIR, "system_metrics.json")
    with open(meta_file, "w") as f:
        json.dump(metadata, f, indent=4)
        
    # 3. Create the final ZIP archive
    zip_filename = f"Garza_Global_Graviton_SBIR_Submission_{datetime.utcnow().strftime('%Y%m%d')}.zip"
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(meta_file, arcname="system_metrics.json")
        if backup_path and os.path.exists(backup_path):
            zipf.write(backup_path, arcname=os.path.basename(backup_path))
            # Include hash if exists
            hash_path = f"{backup_path}.sha256"
            if os.path.exists(hash_path):
                zipf.write(hash_path, arcname=os.path.basename(hash_path))
                
    print(f"✅ Success! Submission archive compiled: {zip_filename}")

if __name__ == "__main__":
    build_submission_package()