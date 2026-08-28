import pytest

from airgap_attestation.merkle import (
    MerkleTree,
    decode_proof,
    encode_proof,
    leaf_hash,
    node_hash,
)


def test_single_leaf_root_is_leaf_hash():
    tree = MerkleTree([b"only-leaf"])
    assert tree.root == leaf_hash(b"only-leaf")
    assert tree.leaf_count == 1


def test_two_leaves_root_matches_manual_computation():
    tree = MerkleTree([b"a", b"b"])
    expected = node_hash(leaf_hash(b"a"), leaf_hash(b"b"))
    assert tree.root == expected


def test_odd_leaf_count_promotes_lone_node_without_duplication():
    """3 leaves must NOT produce the same root as 4 leaves with the last
    one duplicated -- that's the classic Merkle tree forgery weakness."""
    tree_three = MerkleTree([b"a", b"b", b"c"])
    tree_duplicated = MerkleTree([b"a", b"b", b"c", b"c"])
    assert tree_three.root != tree_duplicated.root


def test_leaf_and_internal_domains_are_separated():
    """A two-leaf tree's root must not collide with hashing the two leaves
    as if they were raw (undomained) internal node inputs."""
    tree = MerkleTree([b"a", b"b"])
    naive_concat_hash = leaf_hash(leaf_hash(b"a") + leaf_hash(b"b"))
    assert tree.root != naive_concat_hash


def test_empty_tree_raises():
    with pytest.raises(ValueError):
        MerkleTree([])


@pytest.mark.parametrize("leaf_count", [1, 2, 3, 5, 8, 13])
def test_proof_round_trips_for_every_leaf(leaf_count):
    leaves = [f"leaf-{i}".encode() for i in range(leaf_count)]
    tree = MerkleTree(leaves)
    for index, leaf in enumerate(leaves):
        proof = tree.proof(index)
        assert MerkleTree.verify_proof(leaf, proof, tree.root)


def test_proof_fails_for_wrong_leaf_data():
    leaves = [b"a", b"b", b"c", b"d", b"e"]
    tree = MerkleTree(leaves)
    proof = tree.proof(2)
    assert not MerkleTree.verify_proof(b"tampered", proof, tree.root)


def test_proof_fails_against_wrong_root():
    leaves = [b"a", b"b", b"c"]
    tree = MerkleTree(leaves)
    other_tree = MerkleTree([b"x", b"y", b"z"])
    proof = tree.proof(0)
    assert not MerkleTree.verify_proof(b"a", proof, other_tree.root)


def test_out_of_range_index_raises():
    tree = MerkleTree([b"a", b"b"])
    with pytest.raises(IndexError):
        tree.proof(2)


def test_encode_decode_proof_round_trip():
    tree = MerkleTree([b"a", b"b", b"c", b"d", b"e"])
    proof = tree.proof(3)
    encoded = encode_proof(proof)
    decoded = decode_proof(encoded)
    assert MerkleTree.verify_proof(b"d", decoded, tree.root)
