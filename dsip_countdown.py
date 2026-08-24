"""
dsip_countdown.py - DSIP Release 5 Submission Window Tracker
Calculates time remaining until the Department of Defense portal opening on August 26, 2026.
"""

from datetime import datetime

def check_dsip_window():
    target_date = datetime(2026, 8, 26, 0, 0, 0)
    now = datetime.now()
    
    delta = target_date - now
    
    print("==================================================")
    print("   DEFENSE SBIR/STTR INNOVATION PORTAL (DSIP)      ")
    print("   Release 5 Submission Window Tracker            ")
    print("==================================================")
    
    if delta.total_seconds() > 0:
        days = delta.days
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60
        print(f"⏳ Time until window opens (August 26, 2026):")
        print(f"   {days} days, {hours} hours, and {minutes} minutes remaining.")
    else:
        print("🚨 DSIP Release 5 Submission Window is OPEN NOW!")

if __name__ == "__main__":
    check_dsip_window()