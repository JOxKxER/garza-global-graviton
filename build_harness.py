import os
import sys
import time
import subprocess
import json
import datetime

# Force UTF-8 encoding for standard streams on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

def run_step(title, command):
    print(f"\n[RUNNING STEP] {title}...")
    start_time = time.time()
    
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    result = subprocess.run(
        [sys.executable, command], 
        capture_output=True, 
        text=True, 
        encoding="utf-8", 
        errors="replace",
        env=env
    )
    duration = time.time() - start_time
    
    if result.returncode == 0:
        print(f"  + SUCCESS ({duration:.3f}s)")
        return True, result.stdout
    else:
        print(f"  + FAILED ({duration:.3f}s)")
        print(f"     Error Output:\n{result.stderr}")
        return False, result.stderr

def main():
    print("=" * 65)
    print(" GARZA GLOBAL GRAVITON: MASTER ORCHESTRATION & BUILD HARNESS")
    print("=" * 65)

    steps = [
        ("Code Sanitizer & Syntax Audit",      "code_sanitizer.py"),
        ("Threshold Cryptography Quorum",      "threshold_vault.py"),
        ("Fault Injection & Security Sweep",  "fault_injector.py"),
        ("Single Socket Mesh Handshake",       "mesh_listener.py"),
        ("Multi-Node Concurrent Broadcast",    "multi_node_mesh.py"),
        ("Dynamic Port Failover Router",       "mesh_failover_router.py"),
        ("P2P Network Stress & Jitter",        "mesh_network_stress.py"),
        ("Dynamic P2P Mesh Topology Graph",    "mesh_graph.py"),
        ("Real-Time Peer Discovery Daemon",    "mesh_ping_daemon.py"),
        ("Adaptive Mesh Consensus Engine",     "mesh_consensus.py"),
        ("Automated System Telemetry Audit",   "system_telemetry.py"),
        ("Vector Mesh Self-Healing Engine",    "mesh_heal.py"),
        ("Sovereign Ledger Hash Chain Auditor", "ledger_audit.py"),
        ("Snapshot Engine Backup",             "snapshot_engine.py"),
        ("Vault Cryptographic Sealer",        "vault_sealer.py"),
        ("Vault Seal Verifier",               "seal_verifier.py")
    ]

    passed_steps = 0
    total_steps = len(steps)

    for title, cmd in steps:
        success, _ = run_step(title, cmd)
        if success:
            passed_steps += 1

    print("\n" + "=" * 65)
    print(f" HARNESS SUMMARY: {passed_steps}/{total_steps} STEPS PASSED")
    print("=" * 65)

    # Log execution to sovereign ledger
    ledger_path = os.path.join("..", "04_Legal_and_IP", "sovereign_ledger.json")
    if os.path.exists(ledger_path):
        try:
            with open(ledger_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            entry = {
                "event": "16_STEP_BUILD_HARNESS_COMPLETE",
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
                "score": f"{passed_steps}/{total_steps}",
                "status": "ALL_PASS" if passed_steps == total_steps else "PARTIAL_FAIL"
            }
            data.append(entry)
            with open(ledger_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            print("[STATUS] Build harness completion logged to sovereign_ledger.json")
        except Exception as e:
            print(f"[WARNING] Could not update ledger: {e}")

    print("\n--- Master Build Harness Execution Complete ---")

if __name__ == "__main__":
    main()