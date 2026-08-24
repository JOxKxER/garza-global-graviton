"""
human_data_crunch.py - Distributed Cognitive Network & Worker Task Engine
Manages decentralized data verification, asynchronous review queues, and token-based incentives 
for remote operators across the Garza Global Graviton ecosystem.
"""

import db_manager as db
import pandas as pd

class HumanDataCrunchEngine:
    def __init__(self):
        print("🌐 Initializing Human Data Crunch Distributed Cognitive Network...")
        db.init_db()

    def list_pending_verification_tasks(self):
        """Retrieves all pending verification tasks from the network queue."""
        tasks = db.get_crunch_tasks()
        if tasks:
            return pd.DataFrame(tasks)
        return pd.DataFrame(columns=["id", "task_description", "status", "assigned_worker", "created_at"])

    def assign_task_to_worker(self, task_id, worker_handle):
        """Assigns a distributed verification task to an active network participant."""
        print(f"📌 Assigning Task ID {task_id} to operator: {worker_handle}")
        # Placeholder for DB assignment logic or status update
        return True

    def complete_task_and_reward(self, worker_handle, task_id, reward_tokens=50):
        """Marks a task as completed and distributes $DMS-GRAV or network tokens to the worker."""
        db.award_user_tokens(worker_handle, reward_tokens)
        print(f"✅ Task {task_id} completed by {worker_handle}. Awarded {reward_tokens} tokens.")
        return True

if __name__ == "__main__":
    engine = HumanDataCrunchEngine()
    
    # Quick CLI Demo
    print("\n--- Current Pending Network Tasks ---")
    df_tasks = engine.list_pending_verification_tasks()
    print(df_tasks if not df_tasks.empty else "No active tasks in the queue. Ready for deployment.")