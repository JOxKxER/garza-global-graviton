"""
integrations/payment_gateway.py - Commercial Payment & Advertiser API Gateway
Handles credit card webhooks (Stripe/Square mock) to fund token budgets automatically.
"""

import db_manager as db

def process_successful_payment(company_name, email, amount_paid_usd):
    """Converts fiat payment into platform token credits and updates advertiser status."""
    tokens_earned = int(amount_paid_usd * 100)
    
    db.register_advertiser(
        company=company_name,
        email=email,
        copy=f"Automated Commercial Ad Placement - Funded via Gateway",
        url="https://garzaglobalgraviton.com/partner",
        budget=tokens_earned,
        nsfw_pass=True
    )
    
    db.award_user_tokens(company_name.replace(" ", "_"), tokens_earned)
    print(f"💰 Payment processed for {company_name}: ${amount_paid_usd} USD -> {tokens_earned} tokens credited.")
    return tokens_earned