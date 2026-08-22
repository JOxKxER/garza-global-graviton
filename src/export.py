import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Union, List, Tuple, Dict, Any, Generator
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from src.core import (
    compute_power_spectral_density,
    calculate_shannon_entropy,
    calculate_spectral_entropy,
    hash_numpy_array,
    MerkleTree
)

logger = logging.getLogger(__name__)

# --- Persistent Append-Only JSONL Audit Ledger ---

class AuditLedger:
    """
    Manages an append-only JSONL ledger for cryptographic verification receipts,
    Merkle roots, and block metadata.
    """
    def __init__(self, ledger_path: Union[str, Path] = "output/audit_ledger.jsonl"):
        self.path = Path(ledger_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.touch()

    def get_latest_receipt(self) -> Union[Dict[str, Any], None]:
        """Returns the most recent receipt record in the ledger."""
        latest = None
        for record in self.stream_records():
            latest = record
        return latest

    def append_block_receipt(
        self,
        block_receipt: Dict[str, Any],
        operator: str = "system"
    ) -> Dict[str, Any]:
        """
        Appends a block or Merkle root receipt record with timestamp metadata.
        """
        latest = self.get_latest_receipt()
        sequence_num = (latest["sequence"] + 1) if latest and "sequence" in latest else 0
        ledger_prev_hash = latest["receipt_hash"] if latest and "receipt_hash" in latest else "0" * 64

        import hashlib
        record = {
            "sequence": sequence_num,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ledger_previous_hash": ledger_prev_hash,
            "operator": operator,
            "payload": block_receipt
        }

        # Cryptographically chain the ledger entry itself
        raw_header = f"{record['sequence']}|{record['timestamp']}|{record['ledger_previous_hash']}|{json.dumps(block_receipt, sort_keys=True)}".encode("utf-8")
        record["receipt_hash"] = hashlib.sha256(raw_header).hexdigest()

        with open(self.path, mode="a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

        logger.info(f"Appended receipt #{record['sequence']} to ledger: {self.path.name}")
        return record

    def append_merkle_batch(
        self,
        merkle_tree: MerkleTree,
        batch_id: str,
        metadata: Union[Dict[str, Any], None] = None
    ) -> Dict[str, Any]:
        """
        Extracts Merkle root, leaf count, and metadata, writing a verified batch receipt.
        """
        receipt_payload = {
            "type": "merkle_batch",
            "batch_id": batch_id,
            "merkle_root": merkle_tree.root,
            "total_leaves": len(merkle_tree.leaf_hashes),
            "leaf_hashes": merkle_tree.leaf_hashes,
            "custom_metadata": metadata or {}
        }
        return self.append_block_receipt(receipt_payload)

    def stream_records(self) -> Generator[Dict[str, Any], None, None]:
        """Streams entries line-by-line without loading entire file into memory."""
        if not self.path.exists():
            return
        with open(self.path, mode="r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                clean = line.strip()
                if clean:
                    try:
                        yield json.loads(clean)
                    except json.JSONDecodeError as err:
                        logger.error(f"Malformed JSONL on line {line_num}: {err}")

    def verify_ledger_chain(self) -> Tuple[bool, str]:
        """
        Verifies the cryptographic chain across all appended entries in the ledger.
        """
        import hashlib
        prev_hash = "0" * 64
        expected_seq = 0

        for record in self.stream_records():
            if record["sequence"] != expected_seq:
                return False, f"Sequence break at record #{record['sequence']} (expected {expected_seq})"
            if record["ledger_previous_hash"] != prev_hash:
                return False, f"Broken cryptographic chain at sequence #{record['sequence']}"

            # Recalculate hash
            raw = f"{record['sequence']}|{record['timestamp']}|{record['ledger_previous_hash']}|{json.dumps(record['payload'], sort_keys=True)}".encode("utf-8")
            calc_hash = hashlib.sha256(raw).hexdigest()
            if calc_hash != record["receipt_hash"]:
                return False, f"Tampered record detected at sequence #{record['sequence']}"

            prev_hash = record["receipt_hash"]
            expected_seq += 1

        return True, f"Ledger integrity verified across {expected_seq} records."

# --- Existing Visualization & Data Export Routines ---

def generate_spectral_entropy_plot(
    signal: np.ndarray,
    sampling_rate: float = 1000.0,
    bins: int = 30,
    output_image: Union[str, Path] = "output/spectral_entropy_analysis.png"
) -> Path:
    path = Path(output_image)
    path.parent.mkdir(parents=True, exist_ok=True)
    sig = np.asarray(signal, dtype=np.float64).flatten()
    shannon_bits = calculate_shannon_entropy(sig, bins=bins, base=2.0)
    spec_entropy = calculate_spectral_entropy(sig, sampling_rate=sampling_rate)
    freqs, psd = compute_power_spectral_density(sig, sampling_rate=sampling_rate)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5), dpi=130)
    ax1.hist(sig, bins=bins, density=True, color="#1f77b4", edgecolor="black", alpha=0.7, label="Empirical PDF")
    ax1.set_title(f"Amplitude Distribution (Shannon H: {shannon_bits:.3f} bits)", fontsize=11, pad=10)
    ax1.set_xlabel("Signal Amplitude")
    ax1.set_ylabel("Probability Density")
    ax1.grid(True, linestyle=":", alpha=0.6)
    ax1.legend(loc="upper right")

    ax2.semilogy(freqs, psd + 1e-12, color="#d62728", linewidth=1.4, label="Welch-style PSD")
    peak_idx = np.argmax(psd)
    peak_freq = freqs[peak_idx]
    ax2.plot(peak_freq, psd[peak_idx], "o", color="#2ca02c", markersize=6, label=f"Peak: {peak_freq:.1f} Hz")
    ax2.set_title(f"Power Spectral Density (Spectral H: {spec_entropy:.3f})", fontsize=11, pad=10)
    ax2.set_xlabel("Frequency (Hz)")
    ax2.set_ylabel("Power Density (^2 / Hz$)")
    ax2.grid(True, which="both", linestyle=":", alpha=0.6)
    ax2.legend(loc="upper right")

    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path

def generate_tesseract_edges() -> Tuple[np.ndarray, List[Tuple[int, int]]]:
    vertices = np.array([
        [x, y, z, w]
        for x in (-1, 1) for y in (-1, 1) for z in (-1, 1) for w in (-1, 1)
    ], dtype=np.float64)
    edges = []
    num_v = len(vertices)
    for i in range(num_v):
        for j in range(i + 1, num_v):
            if np.sum(np.abs(vertices[i] - vertices[j]) > 1e-5) == 1:
                edges.append((i, j))
    return vertices, edges

def project_4d_to_3d(points_4d: np.ndarray, distance: float = 2.5) -> np.ndarray:
    points = np.asarray(points_4d, dtype=np.float64)
    w = points[:, 3]
    scale = 1.0 / (distance - w)
    return points[:, :3] * scale[:, np.newaxis]

def render_tesseract_frame(
    vertices_3d: np.ndarray,
    edges: List[Tuple[int, int]],
    output_path: Union[str, Path],
    frame_title: str = "4D Tesseract Projection"
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(7, 7), dpi=120)
    ax = fig.add_subplot(111, projection='3d')
    ax.scatter(vertices_3d[:, 0], vertices_3d[:, 1], vertices_3d[:, 2], color='#00d2ff', s=40, edgecolors='black')
    for edge in edges:
        p1, p2 = vertices_3d[edge[0]], vertices_3d[edge[1]]
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]], [p1[2], p2[2]], color='#1f77b4', linewidth=1.2, alpha=0.75)
    ax.set_xlim([-1.5, 1.5])
    ax.set_ylim([-1.5, 1.5])
    ax.set_zlim([-1.5, 1.5])
    ax.set_title(frame_title, fontsize=11, pad=10)
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path

def create_animated_gif(
    image_paths: List[Union[str, Path]],
    output_gif: Union[str, Path] = "output/tesseract_rotation.gif",
    duration_ms: int = 80,
    loop: int = 0
) -> Path:
    out_gif_path = Path(output_gif)
    out_gif_path.parent.mkdir(parents=True, exist_ok=True)
    pil_images = [Image.open(p) for p in image_paths]
    pil_images[0].save(
        out_gif_path, save_all=True, append_images=pil_images[1:],
        duration=duration_ms, loop=loop, optimize=True
    )
    return out_gif_path

def export_4d_rotation_sequence(
    num_frames: int = 24,
    plane: str = "xw",
    output_dir: Union[str, Path] = "output/frames",
    compile_gif: bool = True,
    gif_path: Union[str, Path] = "output/tesseract_rotation.gif"
) -> Tuple[List[Path], Union[Path, None]]:
    from src.core import transform_4d_dataset
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    vertices_4d, edges = generate_tesseract_edges()
    angles = np.linspace(0, 2 * np.pi, num_frames, endpoint=False)
    frame_files = []
    for idx, theta in enumerate(angles):
        rotated_4d = transform_4d_dataset(vertices_4d, theta=theta, plane=plane)
        projected_3d = project_4d_to_3d(rotated_4d, distance=3.0)
        frame_file = out_path / f"frame_{idx:03d}.png"
        render_tesseract_frame(
            projected_3d, edges, frame_file,
            frame_title=f"Tesseract Rotation ({plane.upper()} plane) | {np.degrees(theta):.0f}°"
        )
        frame_files.append(frame_file)
    compiled_gif = None
    if compile_gif and frame_files:
        compiled_gif = create_animated_gif(frame_files, output_gif=gif_path)
    return frame_files, compiled_gif

def save_array_to_csv(data: np.ndarray, output_path: Union[str, Path]) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for val in data:
            writer.writerow([val])
    return path

def generate_pipeline_plot(original: np.ndarray, transformed: np.ndarray, output_image: Union[str, Path]) -> Path:
    path = Path(output_image)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=120)
    ax.plot(original, label="Original Input", marker="o", linestyle="--", color="#1f77b4")
    ax.plot(transformed, label="Transformed Output", marker="s", linestyle="-", color="#2ca02c")
    ax.set_title("Pipeline Signal Transformation", fontsize=12, pad=10)
    ax.set_xlabel("Sample Index")
    ax.set_ylabel("Value")
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path
