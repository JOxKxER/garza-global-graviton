import os
import sys
import subprocess

# Force UTF-8 encoding for standard streams on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def run_script(script_name):
    clear_screen()
    print(f"=== EXECUTING: {script_name} ===\n")
    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        
        result = subprocess.run([sys.executable, script_name], env=env)
        if result.returncode != 0:
            print(f"\n[WARNING] Process exited with non-zero return code: {result.returncode}")
    except Exception as e:
        print(f"\n[ERROR] Could not execute script: {e}")
    
    input("\nPress Enter to return to Master Control Center...")

def display_menu():
    while True:
        clear_screen()
        print("==================================================================")
        print("      GARZA GLOBAL GRAVITON - MASTER CONTROL CENTER               ")
        print("==================================================================")
        print("  [ 1] System Dashboard")
        print("  [ 2] Tactical Edge TUI Dashboard")
        print("  [ 3] Master Integration Suite")
        print("  [ 4] Integration Test Suite")
        print("  [ 5] System Health Telemetry")
        print("  [ 6] Code Sanitizer & Syntax Audit")
        print("  [ 7] Autonomous Code Refactor Engine")
        print("  [ 8] PRD & Context Synthesizer")
        print("  [ 9] Secret Vault File Encryptor")
        print("  [10] Cryptographic Key Rotator")
        print("  [11] Local AI Benchmark Engine")
        print("  [12] Edge Sharding & Reduction Engine")
        print("  [13] P2P Node Sync & Discovery Engine")
        print("  [14] Tactical Edge Payload Dispatcher")
        print("  [15] CMMC / NIST Compliance Engine")
        print("  [16] Air-Gapped Container Packager")
        print("  [17] Release Packager & Manifest Builder")
        print("  [18] Supply-Chain Integrity Verifier")
        print("  [19] Automated Release Doc Generator")
        print("  [20] AFWERX / SBIR Proposal Generator")
        print("  [21] Automated PDF & Document Exporter")
        print("  [22] Local AI Task Router")
        print("  [23] Ledger Analytics Engine")
        print("  [24] Search & Audit Ledger")
        print("  [25] System Config Engine")
        print("  [26] Vault Data Indexer")
        print("  [27] Generate ZIP Snapshot")
        print("  [28] Seal Vault Archive")
        print("  [29] Verify Cryptographic Seal")
        print("  [30] Automated Pre-Shutdown Lockdown")
        print("  [31] Dynamic Vector Mesh Visualizer")
        print("  [32] Threshold Cryptography Engine")
        print("  [33] Fault Injection & Resilience Engine")
        print("  [34] Real Local Socket P2P Mesh Engine")
        print("  [35] Multi-Node Concurrent Broadcast Router")
        print("  [36] Dynamic Port Failover & Retry Router")
        print("  [37] P2P Network Latency & Packet Loss Simulator")
        print("  [38] Dynamic P2P Mesh Topology Graph Visualizer")
        print("  [39] Real-Time Socket Peer Discovery & Ping Daemon")
        print("  [40] Adaptive Mesh Routing & Consensus Engine")
        print("  [41] Automated System Telemetry & Resource Auditor")
        print("  [42] Vector Mesh Shard Redundancy & Self-Healing Engine")
        print("  [43] Sovereign Ledger Integrity & Hash Chain Auditor")
        print("  [ Q] Quit Launcher")
        print("==================================================================")

        choice = input("\nSelect an option (1-43 or Q): ").strip().lower()

        menu_map = {
            "1":  "vault_dashboard.py",
            "2":  "mesh_tui.py",
            "3":  "build_harness.py",
            "4":  "test_suite.py",
            "5":  "health_checker.py",
            "6":  "code_sanitizer.py",
            "7":  "code_refactor_engine.py",
            "8":  "prd_synthesizer.py",
            "9":  "secret_vault.py",
            "10": "key_rotator.py",
            "11": "ai_benchmark.py",
            "12": "edge_sharding_engine.py",
            "13": "mesh_sync.py",
            "14": "mesh_dispatcher.py",
            "15": "cmmc_reporter.py",
            "16": "podman_packager.py",
            "17": "release_packager.py",
            "18": "manifest_verifier.py",
            "19": "release_doc_generator.py",
            "20": "proposal_generator.py",
            "21": "pdf_exporter.py",
            "22": "task_router.py",
            "23": "ledger_analytics.py",
            "24": "ledger_search.py",
            "25": "vault_config.py",
            "26": "data_indexer.py",
            "27": "snapshot_engine.py",
            "28": "vault_sealer.py",
            "29": "seal_verifier.py",
            "30": "vault_lockdown.py",
            "31": "mesh_visualizer.py",
            "32": "threshold_vault.py",
            "33": "fault_injector.py",
            "34": "mesh_listener.py",
            "35": "multi_node_mesh.py",
            "36": "mesh_failover_router.py",
            "37": "mesh_network_stress.py",
            "38": "mesh_graph.py",
            "39": "mesh_ping_daemon.py",
            "40": "mesh_consensus.py",
            "41": "system_telemetry.py",
            "42": "mesh_heal.py",
            "43": "ledger_audit.py"
        }

        if choice == 'q':
            print("\nExiting Control Center. Stay sovereign!")
            break
        elif choice in menu_map:
            run_script(menu_map[choice])
        else:
            input("\n[INVALID CHOICE] Press Enter to try again...")

if __name__ == "__main__":
    display_menu()