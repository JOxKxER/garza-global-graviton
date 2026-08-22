import logging
import numpy as np
from src.core import MerkleTree

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# Generate 5 batch arrays (odd batch count)
batch_data = [
    np.array([10.0, 20.0, 30.0]),
    np.array([40.0, 50.0, 60.0]),
    np.array([70.0, 80.0, 90.0]),
    np.array([100.0, 110.0, 120.0]),
    np.array([130.0, 140.0, 150.0])
]

tree = MerkleTree(batch_data)
logging.info(f"Merkle Root Hash: {tree.root_hash}")

# Audit Leaf 2
target_index = 2
target_array = batch_data[target_index]
audit_proof = tree.generate_audit_proof(target_index)

logging.info(f"Generated Audit Proof for Leaf {target_index} ({len(audit_proof)} hops)")
is_valid = MerkleTree.verify_audit_proof(target_array, audit_proof, tree.root_hash)
logging.info(f"Target Array Verified Against Root: {is_valid}")
