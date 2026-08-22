"""
Garza Global Graviton Core Module
Snapshot Engine Performance & Stress Benchmark
"""
import os
import time
import zipfile
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAPSHOT_DIR = os.path.join(BASE_DIR, "04_Legal_and_IP", "backups")
LEDGER_PATH = os.path.join(BASE_DIR, "04_Legal_and_IP", "sovereign_ledger.json")

def measure_directory_stats(target_dirs):
    """Calculates total uncompressed size and file counts."""
    total_bytes = 0
    file_count = 0
    for folder in target_dirs:
        dir_path = os.path.join(BASE_DIR, folder)
        if not os.path.exists(dir_path):
            continue
        for root, _, files in os.walk(dir_path):
            for f in files:
                if not f.endswith('.zip'):
                    fp = os.path.join(root, f)
                    total_bytes += os.path.getsize(fp)
                    file_count += 1
    return file_count, total_bytes

def run_snapshot_benchmark():
    """Executes a timed snapshot build and records throughput performance."""
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    target_folders = ["01_Docs", "02_PRDs", "03_Source_Code", "04_Legal_and_IP"]
    
    file_count, uncompressed_bytes = measure_directory_stats(target_folders)
    
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"BENCHMARK_SNAPSHOT_{timestamp}.zip"
    zip_path = os.path.join(SNAPSHOT_DIR, zip_filename)

    # Begin high-precision timer
    start_time = time.perf_counter()

    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
        for folder in target_folders:
            dir_path = os.path.join(BASE_DIR, folder)
            if not os.path.exists(dir_path):
                continue
            for root, _, files in os.walk(dir_path):
                for f in files:
                    if f.endswith('.zip'):
                        continue
                    full_path = os.path.join(root, f)
                    rel_path = os.path.relpath(full_path, BASE_DIR)
                    zipf.write(full_path, rel_path)

    elapsed_seconds = time.perf_counter() - start_time
    compressed_bytes = os.path.getsize(zip_path)

    # Metric Calculations
    uncompressed_mb = uncompressed_bytes / (1024 * 1024)
    compressed_mb = compressed_bytes / (1024 * 1024)
    throughput_mb_s = uncompressed_mb / elapsed_seconds if elapsed_seconds > 0 else 0
    compression_ratio = ((uncompressed_bytes - compressed_bytes) / uncompressed_bytes * 100) if uncompressed_bytes > 0 else 0

    return {
        "files_processed": file_count,
        "uncompressed_mb": round(uncompressed_mb, 3),
        "compressed_mb": round(compressed_mb, 3),
        "elapsed_seconds": round(elapsed_seconds, 4),
        "throughput_mb_s": round(throughput_mb_s, 2),
        "compression_ratio": round(compression_ratio, 2),
        "zip_path": zip_path
    }

if __name__ == "__main__":
    print("=== GARZA GLOBAL GRAVITON: SNAPSHOT PERFORMANCE BENCHMARK ===")
    print("Initiating timed compression sweep...\n")

    results = run_snapshot_benchmark()

    print("==============================================================")
    print("   SNAPSHOT PERFORMANCE METRICS SUMMARY")
    print("==============================================================")
    print(f"  [FILES INGESTED]        {results['files_processed']} Files")
    print(f"  [UNCOMPRESSED SIZE]     {results['uncompressed_mb']} MB")
    print(f"  [ARCHIVE SIZE]          {results['compressed_mb']} MB")
    print(f"  [SPACE REDUCTION]       {results['compression_ratio']}% Saved")
    print("  ----------------------------------------------------------")
    print(f"  [EXECUTION TIME]        {results['elapsed_seconds']} Seconds")
    print(f"  [PROCESSING SPEED]      {results['throughput_mb_s']} MB/s Throughput")
    print("==============================================================\n")