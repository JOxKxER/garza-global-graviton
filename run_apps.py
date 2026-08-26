import subprocess
import webbrowser
import os
import time

def start_system():
    print("--------------------------------------------------")
    print("  GARZA GLOBAL // LAUNCHING LOCAL APP ENVIRONMENT  ")
    print("--------------------------------------------------")

    # 1. Start the FastAPI Telemetry Ingestion Server
    print("[1/3] Starting FastAPI Telemetry Node on port 8000...")
    server_process = subprocess.Popen(["python", "server.py"])

    # Wait a moment for the server to bind to the port
    time.sleep(2)

    # 2. Locate the local HTML dashboard
    dashboard_path = os.path.abspath("index.html")
    if os.path.exists(dashboard_path):
        print(f"[2/3] Opening Tactical Dashboard: {dashboard_path}")
        webbrowser.open(f"file://{dashboard_path}")
    else:
        print("[2/3] WARNING: index.html not found in root directory. Skipping browser launch.")

    print("[3/3] System operational. Local endpoints ready for demo.")
    print("--------------------------------------------------")
    print("Press CTRL+C in this terminal to shut down the node.")

    try:
        # Keep the script running to maintain the background server process
        server_process.wait()
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Stopping telemetry node and cleaning up...")
        server_process.terminate()

if __name__ == "__main__":
    start_system()