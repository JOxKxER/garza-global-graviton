import time
from pathlib import Path
from typing import Generator
import numpy as np

DATA_IN_DIR = Path("data_in")
DATA_IN_DIR.mkdir(parents=True, exist_ok=True)

def generate_workload_stream(batch_size: int = 300_000) -> Generator[np.ndarray, None, None]:
    """
    Checks the data_in directory for incoming .npy or .csv matrices.
    Falls back to high-throughput normalized signal vectors if queue is empty.
    """
    while True:
        npy_files = list(DATA_IN_DIR.glob("*.npy"))
        if npy_files:
            target = npy_files[0]
            try:
                raw_data = np.load(target).astype(np.float64).flatten()
                target.unlink()  # Remove once ingested
                print(f"[INGEST] Ingested matrix {target.name} ({len(raw_data):,d} elements)")
                for i in range(0, len(raw_data), batch_size):
                    yield raw_data[i:i + batch_size]
                continue
            except Exception as e:
                print(f"[!] Error loading {target}: {e}")

        # Default streaming workload: Normalized Multivariable Dispersion
        t = time.time()
        synthetic_stream = np.sin(np.linspace(t, t + 100, batch_size)) * np.random.normal(1.0, 0.05, batch_size)
        yield synthetic_stream.astype(np.float64)
