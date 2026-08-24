"""
integrations/twitch_sync.py - Twitch Stream Chat & Reward Bridge
Links Twitch chat activity to automated token rewards for Garza Global Graviton.
"""

import db_manager as db

def process_twitch_chat_reward(username, keyword):
    """Awards tokens or logs verification tasks based on live stream chat commands."""
    keyword = keyword.lower()
    
    if "!graviton" in keyword:
        db.award_user_tokens(username, 50)
        print(f"🎁 Awarded 50 tokens to Twitch user {username} for chat engagement.")
        return "Awarded 50 $DMS-GRAV tokens!"
    elif "!inspect" in keyword:
        db.create_crunch_task(f"Twitch Stream Inspection - {username}", "Requested via live chat command")
        print(f"🔬 Created asynchronous verification task for Twitch user {username}.")
        return "Verification task queued on decentralized mesh!"
    
    return None