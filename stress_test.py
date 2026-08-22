import asyncio
import httpx
import time

# Direct local endpoint for raw throughput benchmarking
URL = "http://127.0.0.1:8000/api/v1/orders/submit"
API_KEY = "ggg_live_secret_key_8899"
CONCURRENT_REQUESTS = 20

async def submit_order(client: httpx.AsyncClient, index: int):
    payload = {
        "client_ref": f"Stress_Test_Client_{index:02d}",
        "element_count": 250000,
        "scale_factor": 1.5
    }
    start = time.perf_counter()
    try:
        res = await client.post(
            URL,
            headers={
                "x-api-key": API_KEY,
                "Content-Type": "application/json",
                "ngrok-skip-browser-warning": "true"
            },
            json=payload,
            timeout=15.0
        )
        elapsed = (time.perf_counter() - start) * 1000
        if res.status_code == 200:
            data = res.json()
            print(f"[OK] Job {index:02d} -> Order ID: {data.get('order_id')} in {elapsed:.1f}ms (Remaining: {data.get('remaining_credits')})")
            return True
        else:
            print(f"[FAIL] Job {index:02d} -> HTTP {res.status_code}: {res.text}")
            return False
    except Exception as e:
        print(f"[ERR] Job {index:02d} -> Exception: {e}")
        return False

async def main():
    print(f"--- Starting Stress Benchmark: {CONCURRENT_REQUESTS} Concurrent Payloads ---")
    print(f"Target: {URL}\n")
    t0 = time.perf_counter()
    async with httpx.AsyncClient() as client:
        tasks = [submit_order(client, i + 1) for i in range(CONCURRENT_REQUESTS)]
        results = await asyncio.gather(*tasks)
    
    total_time = time.perf_counter() - t0
    success = sum(1 for r in results if r)
    total_elements = success * 250000
    
    print("\n==========================================")
    print(f"BENCHMARK COMPLETED in {total_time:.2f}s")
    print(f"Successful Ingestions : {success}/{CONCURRENT_REQUESTS}")
    print(f"Total Workload Ingested: {total_elements:,} elements")
    if total_time > 0 and success > 0:
        print(f"Throughput Rate        : {total_elements / total_time:,.0f} elements/sec")
    print("==========================================")

if __name__ == "__main__":
    asyncio.run(main())
