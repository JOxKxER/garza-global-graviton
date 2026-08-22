import time
import random
import httpx

API_URL = "http://127.0.0.1:8000/api/v1/orders/submit"
API_KEY = "ggg_live_secret_key_8899"

CLIENT_PROFILES = [
    "Lockheed_Aero_Div",
    "DARPA_Edge_Intake",
    "Raytheon_EW_Telemetry",
    "GeneralDynamics_Mesh",
    "Northrop_Sensor_Stream"
]

def run_simulation():
    print("=== Garza Global Graviton: Autonomous Traffic Daemon Started ===")
    print("Streaming synthetic enterprise workloads to local coordinator...\n")
    
    with httpx.Client() as client:
        while True:
            client_ref = random.choice(CLIENT_PROFILES)
            element_count = random.randint(150000, 750000)
            scale = round(random.uniform(1.2, 3.8), 2)
            
            payload = {
                "client_ref": client_ref,
                "element_count": element_count,
                "scale_factor": scale
            }
            
            try:
                res = client.post(
                    API_URL,
                    headers={"x-api-key": API_KEY, "Content-Type": "application/json"},
                    json=payload,
                    timeout=10.0
                )
                if res.status_code == 200:
                    data = res.json()
                    print(f"[DISPATCH] {client_ref:<24} | Elements: {element_count:>7,} | ID: {data['order_id']}")
                else:
                    print(f"[ERROR] HTTP {res.status_code}: {res.text}")
            except Exception as e:
                print(f"[FAIL] Network error: {e}")
                
            sleep_time = random.uniform(2.5, 6.0)
            time.sleep(sleep_time)

if __name__ == "__main__":
    try:
        run_simulation()
    except KeyboardInterrupt:
        print("\nTraffic daemon stopped.")
