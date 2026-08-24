"""
promo_reward_engine.py - ToS-Compliant Promotional Reward Processor
Handles secure token distributions for authorized external promotional actions.
"""

import db_manager as db

def process_promotional_reward(username, promotion_type):
    """
    Rewards users for compliant promotional actions:
    - 'bio_click': Visiting the platform via a creator's authorized bio link.
    - 'audit_share': Sharing a verified clean-play audit report card.
    - 'partner_support': Interacting with a verified sponsor banner on stream.
    """
    reward_tiers = {
        "bio_click": 10,
        "audit_share": 25,
        "partner_support": 50
    }
    
    if promotion_type in reward_tiers:
        tokens = reward_tiers[promotion_type]
        db.award_user_tokens(username, tokens)
        print(f"✅ Success: Awarded {tokens} integrity tokens to '{username}' for action [{promotion_type}].")
        return True
    else:
        print(f"⚠️ Error: Unknown promotion type '{promotion_type}'.")
        return False

if __name__ == "__main__":
    # Test execution
    process_promotional_reward("StreamerFan99", "audit_share")