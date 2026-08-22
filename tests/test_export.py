import pytest
import numpy as np
from pathlib import Path
from src.core import MerkleTree, AuditLedger
from src.export import (
    generate_tesseract_edges,
    project_4d_to_3d,
    generate_spectral_entropy_plot,
    export_4d_rotation_sequence
)

def test_tesseract_topology():
    vertices, edges = generate_tesseract_edges()
    assert vertices.shape == (16, 4)
    assert len(edges) == 32

def test_project_4d_to_3d():
    projected = project_4d_to_3d(np.array([[1.0, 1.0, 1.0, 0.0]]), distance=2.0)
    np.testing.assert_array_almost_equal(projected, [[0.5, 0.5, 0.5]])

def test_generate_spectral_entropy_plot(tmp_path):
    t = np.linspace(0, 1.0, 200)
    sig = np.sin(2 * np.pi * 20.0 * t)
    out_file = tmp_path / "spectral.png"
    p = generate_spectral_entropy_plot(sig, sampling_rate=200.0, output_image=out_file)
    assert p.exists()

def test_audit_ledger_append_and_verify(tmp_path):
    ledger_file = tmp_path / "ledger.json"
    dummy_file = tmp_path / "data.csv"
    dummy_file.write_text("1,2,3,4\n", encoding="utf-8")

    ledger = AuditLedger(ledger_file=ledger_file)
    ledger.append_record(dummy_file, metadata={"tag": "raw_input"})

    valid, msg = ledger.verify_ledger_chain()
    assert valid is True

    # Verify MerkleTree root property works cleanly
    tree = MerkleTree([ledger.entries[0]["file_hash"]])
    assert isinstance(tree.root, str)
    assert len(tree.root) == 64

def test_audit_ledger_detects_file_tampering(tmp_path):
    ledger_file = tmp_path / "ledger.json"
    dummy_file = tmp_path / "data.csv"
    dummy_file.write_text("10,20,30\n", encoding="utf-8")

    ledger = AuditLedger(ledger_file=ledger_file)
    ledger.append_record(dummy_file, metadata={"tag": "secure"})

    # Tamper with the file on disk
    dummy_file.write_text("10,20,9999\n", encoding="utf-8")

    # Verification must fail
    valid, msg = ledger.verify_ledger_chain()
    assert valid is False
    assert "Tampering detected" in msg
