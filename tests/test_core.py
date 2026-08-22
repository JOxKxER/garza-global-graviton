import pytest
import numpy as np
from src.core import (
    MerkleTree,
    hash_numpy_array,
    create_tamper_evident_block,
    verify_block_integrity,
    calculate_shannon_entropy,
    compute_power_spectral_density,
    calculate_spectral_entropy
)

def test_merkle_tree_root_consistency():
    blocks = [np.array([i, i * 2, i * 3], dtype=np.float64) for i in range(4)]
    tree1 = MerkleTree(blocks)
    tree2 = MerkleTree(blocks)
    assert tree1.root_hash == tree2.root_hash
    assert len(tree1.root_hash) == 64

def test_merkle_tree_audit_proof_success():
    blocks = [np.array([i * 1.5, i * 2.5]) for i in range(7)]  # Odd number tests balance
    tree = MerkleTree(blocks)
    root = tree.root_hash

    # Verify every leaf individually
    for idx, block in enumerate(blocks):
        proof = tree.generate_audit_proof(idx)
        assert MerkleTree.verify_audit_proof(block, proof, root) is True

def test_merkle_tree_detects_tampered_leaf():
    blocks = [np.array([1.0, 2.0]), np.array([3.0, 4.0]), np.array([5.0, 6.0])]
    tree = MerkleTree(blocks)
    root = tree.root_hash

    proof = tree.generate_audit_proof(leaf_index=1)
    tampered_block = np.array([3.0, 4.0001])

    assert MerkleTree.verify_audit_proof(tampered_block, proof, root) is False
