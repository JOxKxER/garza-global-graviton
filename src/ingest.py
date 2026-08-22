import csv
import json
from pathlib import Path
from typing import List, Union
import numpy as np
import logging

logger = logging.getLogger(__name__)

def load_numeric_series(file_path: Union[str, Path]) -> np.ndarray:
    """
    Loads numeric rows/series from a CSV or JSON file and converts to a float64 NumPy array.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Source file not found at: {path}")

    logger.info(f"Ingesting data from {path.name}")
    values: List[float] = []

    if path.suffix.lower() == ".csv":
        # 'utf-8-sig' cleanly handles UTF-8 files created by Windows PowerShell or Excel
        with open(path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            for row in reader:
                for item in row:
                    item_str = item.strip()
                    if item_str:
                        try:
                            values.append(float(item_str))
                        except ValueError:
                            continue
    elif path.suffix.lower() == ".json":
        with open(path, mode="r", encoding="utf-8-sig") as f:
            raw_data = json.load(f)
            if isinstance(raw_data, list):
                values = [float(x) for x in raw_data if isinstance(x, (int, float, str)) and str(x).replace(".", "", 1).lstrip("-").isdigit()]
    else:
        raise ValueError(f"Unsupported file format: {path.suffix}")

    if not values:
        raise ValueError(f"No valid numeric data found in {path.name}")

    return np.array(values, dtype=np.float64)
