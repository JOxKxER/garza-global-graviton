"""
adaptive_defense.py - Telemetry Feedback & Adaptive Learning Engine
Analyzes logged security vectors to optimize anti-cheat and security thresholds.
"""

import db_manager as db

def analyze_and_adapt():
    print("==================================================")
    print("🧠 ADAPTIVE DEFENSE & LEARNING ENGINE")
    print("==================================================")

    events = db.get_recent_events(limit=200)
    policies = db.get_policies()

    if not events:
        print("ℹ️ No security events logged yet. System baseline is stable.")
        return

    print(f"📊 Analyzing {len(events)} recent security events for behavioral patterns...")

    # Count vector frequencies
    vector_counts = {}
    for ev in events:
        v = ev['vector']
        vector_counts[v] = vector_counts.get(v, 0) + 1

    print("\n🔍 Detected Threat Vector Frequencies:")
    for vector, count in vector_counts.items():
        print(f"   - [{count} occurrences] {vector}")

    # Adaptive Logic: If aim snaps or velocity spikes are frequent, tighten thresholds dynamically
    current_aim_thresh = policies.get('aim_vector_threshold_deg_per_ms', 65.0)
    current_sigma = policies.get('velocity_deviation_sigma', 2.2)

    aim_snaps = vector_counts.get("Sub-Tick Aim Snap (Exceeds Threshold)", 0)
    
    if aim_snaps >= 3:
        new_aim_thresh = max(45.0, current_aim_thresh - 5.0)
        print(f"\n⚡ Adaptation Triggered: High frequency of aim snaps detected.")
        print(f"   -> Automatically tightening aim vector threshold from {current_aim_thresh}°/ms to {new_aim_thresh}°/ms.")
        
        # Apply updated policy back to database
        db.update_policies(
            auth_pos=policies.get('server_authoritative_position', 1),
            packet_scan=policies.get('sub_tick_packet_scan', 1),
            auto_kick=policies.get('auto_kick_memory_hook', 1),
            vel_sigma=current_sigma,
            aim_thresh=new_aim_thresh,
            discord_webhook=policies.get('discord_webhook_url', '')
        )
        print("✅ Defense baseline successfully updated and hardened.")
    else:
        print("\n✅ Threat frequency within normal parameters. Thresholds remain optimal.")

if __name__ == "__main__":
    analyze_and_adapt()