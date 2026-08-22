import os
import sys
import time
import random
import datetime

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def generate_shard_id():
    return f"0x{random.randint(0x1000, 0xFFFF):X}"

def run_visualizer():
    nodes = {
        "ALPHA":   {"status": "ONLINE",  "latency": 12, "shards": 0},
        "BRAVO":   {"status": "ONLINE",  "latency": 18, "shards": 0},
        "CHARLIE": {"status": "ONLINE",  "latency": 15, "shards": 0},
        "DELTA":   {"status": "STANDBY", "latency": 45, "shards": 0}
    }
    
    total_shards_routed = 0
    active_transfers = []

    try:
        for tick in range(1, 21):
            clear_screen()
            now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            
            # Simulate occasional node telemetry flux
            if tick == 8:
                nodes["BRAVO"]["status"] = "OFFLINE"
                nodes["DELTA"]["status"] = "ONLINE (FAILOVER)"
            elif tick == 15:
                nodes["BRAVO"]["status"] = "RECOVERING"
            elif tick == 18:
                nodes["BRAVO"]["status"] = "ONLINE"
                nodes["DELTA"]["status"] = "STANDBY"

            # Route a new shard
            src = random.choice([n for n, d in nodes.items() if "ONLINE" in d["status"]])
            dst = random.choice([n for n, d in nodes.items() if "ONLINE" in d["status"] and n != src])
            
            shard_id = generate_shard_id()
            nodes[src]["shards"] += 1
            total_shards_routed += 1
            
            active_transfers.append(f"Shard [{shard_id}] :: {src} ---> {dst} ({random.randint(10, 30)}ms)")
            if len(active_transfers) > 4:
                active_transfers.pop(0)

            # Print Visualizer Header
            print("=" * 65)
            print(f" GARZA GLOBAL GRAVITON: DYNAMIC VECTOR MESH VISUALIZER")
            print(f" TIMESTAMP: {now} | CYCLE: {tick}/20")
            print("=" * 65)
            print("\n[NODE TOPOLOGY & TELEMETRY]")
            print(f" {'NODE':<12} | {'STATUS':<20} | {'LATENCY':<10} | {'SHARDS'}")
            print("-" * 65)
            for name, data in nodes.items():
                print(f" {name:<12} | {data['status']:<20} | {data['latency']}ms      | {data['shards']}")
            
            print("\n[LIVE VECTOR SHARD ROUTING LOG]")
            print("-" * 65)
            for tx in active_transfers:
                print(f"  » {tx}")
            
            print("\n[METRICS]")
            print(f"  Total Shards Dispatched : {total_shards_routed}")
            print(f"  Air-Gapped Sync Integrity: 100% VERIFIED")
            print("-" * 65)
            print("\nPress Ctrl+C to interrupt simulation...")
            
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[INFO] Visualizer stream stopped by user.")

    print("\n--- Visualizer Sweep Complete ---")

if __name__ == "__main__":
    run_visualizer()