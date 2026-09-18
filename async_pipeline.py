import asyncio
import aiosqlite
import json
from datetime import datetime

DB_PATH = "V:\\03_Source_Code\\data_in\\mesh_telemetry.db"

async def process_mesh_queue():
    print("Initializing async mesh dispatcher...")
    async with aiosqlite.connect(DB_PATH) as db:
        # Insert a sample pending message to test the pipeline
        await db.execute(
            """INSERT OR IGNORE INTO mesh_messages (message_id, sender, receiver, payload, status) 
               VALUES (?, ?, ?, ?, ?)""",
            ("msg_001", "Node_Alpha", "Node_Beta", json.dumps({"task": "telemetry_sync"}), "pending")
        )
        await db.commit()
        
        # Fetch pending messages
        async with db.execute("SELECT message_id, sender, receiver, payload FROM mesh_messages WHERE status = 'pending'") as cursor:
            async for row in cursor:
                msg_id, sender, receiver, payload = row
                print(f"Processing message {msg_id} from {sender} to {receiver}...")
                await asyncio.sleep(0.5) # Simulate asynchronous data dispatch
                
                # Mark as processed
                await db.execute("UPDATE mesh_messages SET status = 'completed' WHERE message_id = ?", (msg_id,))
                await db.commit()
                print(f"Message {msg_id} successfully synced across mesh.")

if __name__ == "__main__":
    asyncio.run(process_mesh_queue())