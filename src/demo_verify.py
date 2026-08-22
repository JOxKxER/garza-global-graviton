import logging
import numpy as np
from src.core import create_tamper_evident_block, verify_block_integrity

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# 1. Create original dataset
dataset = np.array([[12.4, 45.1, 99.2, 0.4], [33.1, 10.5, 71.0, 8.8]], dtype=np.float64)
block = create_tamper_evident_block(dataset, block_index=0, metadata={"source": "Sensor_Array_Alpha"})

logging.info(f"Block Index: {block['index']}")
logging.info(f"Block Hash:  {block['block_hash']}")
logging.info(f"Data SHA256: {block['data_hash']}")

# 2. Check authentic data
is_valid, msg = verify_block_integrity(block, dataset)
logging.info(f"Authentic Verification: {is_valid} -> {msg}")

# 3. Simulate unauthorized data alteration
corrupted_dataset = dataset.copy()
corrupted_dataset[0, 0] = 12.40001
is_corrupted_valid, corrupt_msg = verify_block_integrity(block, corrupted_dataset)
logging.warning(f"Corrupted Data Verification: {is_corrupted_valid} -> {corrupt_msg}")
