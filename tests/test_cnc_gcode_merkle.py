import pytest

from cnc_attestation.gcode_merkle import (
    GCodeManifestBuilder,
    MerkleTree,
    compute_gcode_commitment,
    leaf_hash,
    node_hash,
    verify_gcode_reveal,
)


def test_single_leaf_root_is_leaf_hash():
    tree = MerkleTree([b"only-leaf"])
    assert tree.root == leaf_hash(b"only-leaf")


def test_odd_leaf_count_promotes_lone_node_without_duplication():
    tree_three = MerkleTree([b"a", b"b", b"c"])
    tree_duplicated = MerkleTree([b"a", b"b", b"c", b"c"])
    assert tree_three.root != tree_duplicated.root


def test_domain_separation_prevents_leaf_node_collision():
    tree = MerkleTree([b"a", b"b"])
    naive = leaf_hash(leaf_hash(b"a") + leaf_hash(b"b"))
    assert tree.root != naive


@pytest.mark.parametrize("leaf_count", [1, 2, 3, 5, 8])
def test_proof_round_trips(leaf_count):
    leaves = [f"line-{i}".encode() for i in range(leaf_count)]
    tree = MerkleTree(leaves)
    for i, leaf in enumerate(leaves):
        proof = tree.proof(i)
        assert MerkleTree.verify_proof(leaf, proof, tree.root)


def test_commit_reveal_round_trip():
    gcode = b"G1 X10 Y0 F800\nG1 X10 Y10\n"
    salt = b"0123456789abcdef"
    commitment = compute_gcode_commitment(gcode, salt)
    assert verify_gcode_reveal(gcode, salt, commitment)


def test_commit_reveal_rejects_substituted_gcode():
    gcode = b"G1 X10 Y0 F800\n"
    salt = b"0123456789abcdef"
    commitment = compute_gcode_commitment(gcode, salt)
    assert not verify_gcode_reveal(b"G1 X99 Y99 F800\n", salt, commitment)


def test_manifest_builder_seals_expected_event_sequence():
    builder = GCodeManifestBuilder(commitment_id="c1", job_salt=b"job-salt-bytes12")
    builder.record_job_start("test-job", total_lines=2)
    builder.record_line_executed(0, "G1 X10 Y0")
    builder.record_tool_change("T1")
    builder.record_spindle_state(rpm=10000, enabled=True)
    builder.record_line_executed(1, "G1 X10 Y10")
    builder.record_job_end(lines_executed=2, completed=True)
    manifest = builder.seal()

    assert manifest.leaf_count == 6
    event_types = [e.event_type.value for e in manifest.events]
    assert event_types == [
        "JOB_START",
        "LINE_EXECUTED",
        "TOOL_CHANGE",
        "SPINDLE_STATE",
        "LINE_EXECUTED",
        "JOB_END",
    ]


def test_manifest_line_hash_is_deterministic_per_job_salt():
    builder = GCodeManifestBuilder(commitment_id="c1", job_salt=b"fixed-salt-value")
    assert builder.line_hash("G1 X10 Y0") == builder.line_hash("G1 X10 Y0")

    other_builder = GCodeManifestBuilder(commitment_id="c1", job_salt=b"different-salt!!")
    assert builder.line_hash("G1 X10 Y0") != other_builder.line_hash("G1 X10 Y0")


def test_seal_raises_on_empty_manifest():
    builder = GCodeManifestBuilder(commitment_id="c1", job_salt=b"job-salt-bytes12")
    with pytest.raises(ValueError):
        builder.seal()
