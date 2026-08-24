"""
test_sandbox_client.py - Automated Sandbox API Client Test
Simulates an external developer or AI agent interacting with the Garza Global Graviton 
FastAPI gateway to verify telemetry endpoints and task submissions.
"""

import requests
import sqlite3

API_URL = "http://localhost:8000"
DB_NAME = "vault_storage.db"

def get_active_sandbox_key():
    """Retrieves a valid active sandbox session ID directly from the local vault."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT session_id, developer_entity FROM ai_sandbox_sessions WHERE status = 'ACTIVE' LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        return row if row else (None, None)
    except Exception as e:
        print(f"❌ Error retrieving session key: {e}")
        return None, None

def run_client_integration_test():
    print("==================================================")
    print("   GARZA GLOBAL GRAVITON: SANDBOX API CLIENT TEST ")
    print("==================================================")

    session_id, entity = get_active_sandbox_key()
    if not session_id:
        print("⚠️ No active sandbox session found in vault.")
        print("💡 Tip: Run your ai_sandbox_gateway.py script first to generate a test session key.")
        return

    print(f"🔑 Using Session ID for [{entity}]: {session_id}")
    headers = {"X-API-Key": session_id}

    # 1. Test Telemetry Endpoint
    print("\n[1/2] Testing GET /sandbox/telemetry-status...")
    try:
        response = requests.get(f"{API_URL}/sandbox/telemetry-status", headers=headers)
        if response.status_code == 200:
            print("✅ Telemetry Check SUCCESS:")
            print(response.json())
        else:
            print(f"❌ Failed: Status Code {response.status_code} - {response.text}")
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Ensure your FastAPI server is running (`python -m uvicorn ai_sandbox_api:app --reload`)")
        return

    # 2. Test Task Submission Endpoint
    print("\n[2/2] Testing POST /sandbox/submit-verification...")
    payload = {
        "task_description": "Validate decentralized packet routing hash for tactical edge node 04.",
        "target_entity": "External_AI_Evaluator"
    }
    try:
        response = requests.post(f"{API_URL}/sandbox/submit-verification", json=payload, headers=headers)
        if response.status_code == 200:
            print("✅ Task Submission SUCCESS:")
            print(response.json())
        else:
            print(f"❌ Failed: Status Code {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error submitting task: {e}")

    print("\n==================================================")
    print("   CLIENT INTEGRATION TEST COMPLETE               ")
    print("==================================================")

if __name__ == "__main__":
    run_client_integration_test()