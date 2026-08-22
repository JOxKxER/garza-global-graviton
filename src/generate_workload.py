import time
import argparse
from pathlib import Path
import numpy as np

DATA_IN_DIR = Path("data_in")
DATA_IN_DIR.mkdir(parents=True, exist_ok=True)

def generate_matrices(count: int = 5, size: int = 600_000):
    print(f"[*] Generating {count} dataset batches ({size:,d} float64 elements each)...")
    for i in range(count):
        filename = DATA_IN_DIR / f"workload_batch_{int(time.time())}_{i+1}.npy"
        # Generate structured 4D-rotation tensor data
        data = np.random.standard_normal(size).astype(np.float64)
        np.save(filename, data)
        print(f"[+] Staged {filename.name} ({data.nbytes / (1024*1024):.2f} MB)")
        time.sleep(0.5)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=5, help="Number of files to stage")
    parser.add_argument("--size", type=int, default=600_000, help="Elements per file")
    args = parser.parse_args()
    generate_matrices(args.count, args.size)
