"""
test_discord.py - Test Script for Discord Alert Relay
Triggers a live test message through your configured webhook.
"""

from integrations.discord_notifier import send_discord_alert

if __name__ == "__main__":
    print("🚀 Dispatching test notification to Discord...")
    success = send_discord_alert(
        title="System Integration Test", 
        message="Garza Global Graviton telemetry and webhook relay are fully operational."
    )
    if success:
        print("🎉 Check your Discord channel—the alert should be visible!")
    else:
        print("❌ Failed to send alert. Make sure you ran 'python setup_discord.py' first.")