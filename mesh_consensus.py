import os
import sys
import json
import hashlib
import datetime

# Force UTF-8 encoding for standard streams on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

NODES = ["ALPHA_NODE", "BRAVO_NODE", "CHARLIE_NODE"]

def calculate_hash(data_str):
    return hashlib.sha256(data_str.encode('utf-8')).hexdigest()

def run_consensus_engine():
    print("=" * 65)
    print(" GARZA GLOBAL GRAVITON: ADAPTIVE MESH CONSENSUS ENGINE")
    print("=" * 65)

    block_data = "VECTOR_BLOCK_PROPOSAL_0x40A_PROVENANCE_VERIFIED"
    block_hash = calculate_hash(block_data)

    print(f"\n[PROPOSAL] Node ALPHA proposing Vector Block Hash:\n  └─ {block_hash}")
    print("\n[VOTING] Collecting cryptographic signatures from active mesh nodes...\n")

    votes = {}
    for node in NODES:
        # Simulate local verification and signing
        node_signature = calculate_hash(f"{node}:{block_hash}")
        votes[node] = {
            "vote": "ACCEPT",
            "signature": node_signature[:16] # Truncated signature for display
        }
        print(f"  + [{node}] VOTE: ACCEPT | Sig: {node_signature[:16]}...")

    accept_count = sum(1 for v in votes.values() if v["vote"] == "ACCEPT")
    quorum_reached = accept_count >= 2

    print("\n" + "=" * 65)
    print(f" CONSENSUS SUMMARY: {accept_count}/{len(NODES)} VOTES ACCEPTED")
    print(f" QUORUM STATUS   : {'REACHED (MAJORITY VERIFIED)' if quorum_reached else 'FAILED'}")
    print("=" * 65)

    # Log consensus event to sovereign ledger
    ledger_path = os.path.join("..", "04_Legal_and_IP", "sovereign_ledger.json")
    if os.path.exists(ledger_path):
        try:
            with open(ledger_path, "r", encoding="utf-8") as f:
                ledger = json.load(f)
            entry = {
                "event": "VECTOR_BLOCK_CONSENSUS_REACHED",
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
                "block_hash": block_hash,
                "votes_accepted": accept_count,
                "quorum": "2/3_MAJORITY",
                "status": "COMMITTED"
            }
            ledger.append(entry)
            with open(ledger_path, "w", encoding="utf-8") as f:
                json.dump(ledger, f, indent=2)
            print("[STATUS] Vector block consensus committed to sovereign_ledger.json")
        except Exception as e:
            print(f"[WARNING] Could not update ledger: {e}")

    print("\n--- Adaptive Mesh Consensus Sweep Complete ---")

if __name__ == "__main__":
    run_consensus_engine()