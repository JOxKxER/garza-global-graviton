import os
import sys
import json
import secrets
import datetime

# Simple implementation of threshold secret splitting (2-of-3 scheme)
def split_secret(secret_int, num_shares=3, threshold=2):
    # Generating polynomial coefficients: f(x) = secret + a1*x
    a1 = secrets.randbelow(10**6) + 1
    shares = []
    for x in range(1, num_shares + 1):
        y = secret_int + a1 * x
        shares.append((x, y))
    return shares

def reconstruct_secret(shares):
    # Lagrange interpolation for k=2 threshold at x=0
    (x0, y0), (x1, y1) = shares[0], shares[1]
    # f(0) = y0*x1/(x1-x0) + y1*x0/(x0-x1)
    secret = (y0 * x1 - y1 * x0) // (x1 - x0)
    return secret

def run_threshold_demo():
    print("=" * 65)
    print(" GARZA GLOBAL GRAVITON: THRESHOLD CRYPTOGRAPHY ENGINE")
    print(" Scheme: 2-of-3 Quorum Secret Sharing")
    print("=" * 65)

    # 1. Generate Master Key
    master_key = secrets.randbelow(899999) + 100000
    print(f"\n[GENERATED MASTER KEY] : {master_key}")

    # 2. Split Key into 3 Edge Node Shares
    shares = split_secret(master_key, num_shares=3, threshold=2)
    print("\n[SPLITTING MASTER KEY INTO 3 NODE SHARES]")
    node_names = ["ALPHA_NODE", "BRAVO_NODE", "CHARLIE_NODE"]
    for i, (x, y) in enumerate(shares):
        print(f"  » Share {x} ({node_names[i]}) : KeyFragment({x}, {y})")

    # 3. Simulate Reconstruction with 2 Shares (Quorum Met)
    quorum_shares = [shares[0], shares[2]]  # Using ALPHA and CHARLIE
    print("\n[SIMULATING KEY RECONSTRUCTION]")
    print(f"  Attempting unlock using {node_names[0]} and {node_names[2]}...")
    
    reconstructed_key = reconstruct_secret(quorum_shares)
    print(f"  Reconstructed Key     : {reconstructed_key}")

    # 4. Quorum Verification Check
    if reconstructed_key == master_key:
        print("\n[SUCCESS] Key Quorum Verified! Master Vault Unlocked.")
        
        # Log to ledger
        ledger_path = os.path.join("..", "04_Legal_and_IP", "sovereign_ledger.json")
        if os.path.exists(ledger_path):
            try:
                with open(ledger_path, "r") as f:
                    data = json.load(f)
                entry = {
                    "event": "THRESHOLD_KEY_QUORUM_VERIFIED",
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
                    "scheme": "2-of-3",
                    "status": "PASS"
                }
                data.append(entry)
                with open(ledger_path, "w") as f:
                    json.dump(data, f, indent=2)
                print("[STATUS] Event logged to sovereign_ledger.json")
            except Exception as e:
                print(f"[WARNING] Could not update ledger: {e}")
    else:
        print("\n[ERROR] Quorum Failed! Key Mismatch.")

    print("\n--- Threshold Cryptography Execution Complete ---")

if __name__ == "__main__":
    run_threshold_demo()