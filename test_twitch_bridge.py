"""
test_twitch_bridge.py - Interactive Simulation for Twitch Stream Chat Rewards
Simulates live chat commands like '!graviton' or '!inspect' to test token rewards.
"""

from integrations.twitch_sync import process_twitch_chat_reward
import db_manager as db

def simulate_chat():
    print("🎮 Initializing Twitch Stream Chat Simulator...")
    username = "Danville_Engineer"
    
    print(f"\n--- Simulating Chat Event 1 ---")
    print(f"User '{username}' types: '!graviton'")
    res1 = process_twitch_chat_reward(username, "!graviton")
    print(f"🤖 Bot Response: {res1}")
    print(f"💰 Current Token Balance for {username}: {db.get_user_tokens(username)} $DMS-GRAV")

    print(f"\n--- Simulating Chat Event 2 ---")
    print(f"User '{username}' types: '!inspect turbine blade tolerances'")
    res2 = process_twitch_chat_reward(username, "!inspect turbine blade tolerances")
    print(f"🤖 Bot Response: {res2}")
    
    print("\n✅ Twitch chat bridge simulation completed successfully!")

if __name__ == "__main__":
    simulate_chat()