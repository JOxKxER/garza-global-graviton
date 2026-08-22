import pytest
import numpy as np
from pathlib import Path
from src.ingest import load_numeric_series

def test_load_sample_csv():
    csv_path = Path("data/sample.csv")
    arr = load_numeric_series(csv_path)
    assert isinstance(arr, np.ndarray)
    assert len(arr) == 9
    assert arr[0] == 12.5

def test_missing_file_raises_error():
    with pytest.raises(FileNotFoundError):
        load_numeric_series("data/non_existent.csv")
