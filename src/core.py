import hashlib
import json
import logging
from pathlib import Path
from typing import Union, Tuple, Dict, Any, List
import numpy as np

logger = logging.getLogger(__name__)

# --- Cryptographic & Data Integrity Verification ---

def hash_numpy_array(data: np.ndarray) -> str:
    arr = np.ascontiguousarray(data)
    hasher = hashlib.sha256()
    metadata = f"{arr.dtype.str}:{arr.shape}:".encode("utf-8")
    hasher.update(metadata)
    hasher.update(arr.tobytes())
    return hasher.hexdigest()

def hash_file_sha256(file_path: Union[str, Path]) -> str:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

def _to_hex_leaf(item: Any) -> str:
    if isinstance(item, np.ndarray):
        return hash_numpy_array(item)
    elif isinstance(item, bytes):
        return hashlib.sha256(item).hexdigest()
    elif isinstance(item, str):
        if len(item) == 64 and all(c in "0123456789abcdefABCDEF" for c in item):
            return item.lower()
        return hashlib.sha256(item.encode("utf-8")).hexdigest()
    else:
        return hashlib.sha256(str(item).encode("utf-8")).hexdigest()

class MerkleTree:
    """
    Hierarchical Merkle Tree implementation supporting dynamic proof generation and verification.
    """
    def __init__(self, leaves: List[Any] = None):
        self.raw_leaves = leaves or []
        self.leaves: List[str] = [_to_hex_leaf(x) for x in self.raw_leaves]
        self.levels: List[List[str]] = []
        self._build_tree()

    @property
    def root(self) -> str:
        return self._root

    @property
    def root_hash(self) -> str:
        return self._root

    def _build_tree(self):
        if not self.leaves:
            self._root = "0" * 64
            self.levels = [[]]
            return

        self.levels = [self.leaves[:]]
        current_level = self.leaves[:]

        while len(current_level) > 1:
            if len(current_level) % 2 == 1:
                current_level.append(current_level[-1])

            next_level = []
            for i in range(0, len(current_level), 2):
                combined = (current_level[i] + current_level[i + 1]).encode("utf-8")
                next_level.append(hashlib.sha256(combined).hexdigest())
            
            self.levels.append(next_level)
            current_level = next_level

        self._root = current_level[0]

    def add_leaf(self, leaf: Any):
        self.leaves.append(_to_hex_leaf(leaf))
        self._build_tree()

    def generate_audit_proof(self, leaf_index: int) -> List[Dict[str, str]]:
        """
        Generates cryptographic audit trail (sibling hashes and directions) for a leaf index.
        """
        if leaf_index < 0 or leaf_index >= len(self.leaves):
            raise IndexError("Leaf index out of bounds.")

        proof = []
        idx = leaf_index

        for level in self.levels[:-1]:
            # Handle odd-sized level duplication
            level_nodes = level[:]
            if len(level_nodes) % 2 == 1:
                level_nodes.append(level_nodes[-1])

            is_right = (idx % 2 == 1)
            sibling_idx = idx - 1 if is_right else idx + 1
            sibling_hash = level_nodes[sibling_idx]

            proof.append({
                "sibling": sibling_hash,
                "position": "left" if is_right else "right"
            })
            idx //= 2

        return proof

    @staticmethod
    def verify_audit_proof(leaf: Any, proof: List[Dict[str, str]], expected_root: str) -> bool:
        """
        Verifies a leaf hash against an expected Merkle root using an audit proof path.
        """
        current_hash = _to_hex_leaf(leaf)

        for p in proof:
            sibling = p["sibling"]
            if p["position"] == "left":
                combined = (sibling + current_hash).encode("utf-8")
            else:
                combined = (current_hash + sibling).encode("utf-8")
            current_hash = hashlib.sha256(combined).hexdigest()

        return current_hash == expected_root

class AuditLedger:
    def __init__(self, ledger_file: Union[str, Path] = "output/audit_ledger.json"):
        self.ledger_path = Path(ledger_file)
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self.entries: List[Dict[str, Any]] = []
        self.load()

    def load(self):
        if self.ledger_path.exists():
            try:
                with open(self.ledger_path, "r", encoding="utf-8") as f:
                    self.entries = json.load(f)
            except Exception:
                self.entries = []

    def save(self):
        with open(self.ledger_path, "w", encoding="utf-8") as f:
            json.dump(self.entries, f, indent=2)

    def append_record(self, file_path: Union[str, Path], metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        path = Path(file_path)
        file_hash = hash_file_sha256(path)
        prev_hash = self.entries[-1]["entry_hash"] if self.entries else "0" * 64
        index = len(self.entries)

        meta = metadata or {}
        record_payload = f"{index}|{prev_hash}|{file_hash}|{sorted(meta.items())}".encode("utf-8")
        entry_hash = hashlib.sha256(record_payload).hexdigest()

        entry = {
            "index": index,
            "file_path": str(path),
            "file_hash": file_hash,
            "previous_hash": prev_hash,
            "entry_hash": entry_hash,
            "metadata": meta
        }
        self.entries.append(entry)
        self.save()
        return entry

    def verify_ledger_chain(self) -> Tuple[bool, str]:
        if not self.entries:
            return True, "Ledger is empty."

        for i, entry in enumerate(self.entries):
            target_file = Path(entry["file_path"])
            if not target_file.exists():
                return False, f"File missing on disk: {target_file}"
            
            actual_file_hash = hash_file_sha256(target_file)
            if actual_file_hash != entry["file_hash"]:
                return False, f"Tampering detected on {target_file}! Hash mismatch."

            expected_prev = "0" * 64 if i == 0 else self.entries[i - 1]["entry_hash"]
            if entry["previous_hash"] != expected_prev:
                return False, f"Chain broken at entry {i}!"

            payload = f"{entry['index']}|{entry['previous_hash']}|{entry['file_hash']}|{sorted(entry['metadata'].items())}".encode("utf-8")
            if hashlib.sha256(payload).hexdigest() != entry["entry_hash"]:
                return False, f"Entry header tampered at index {i}."

        return True, "All ledger entries and file artifacts verified successfully."

def create_tamper_evident_block(
    data: np.ndarray,
    block_index: int = 0,
    previous_hash: str = "0" * 64,
    metadata: Union[Dict[str, Any], None] = None
) -> Dict[str, Any]:
    data_hash = hash_numpy_array(data)
    meta = metadata or {}
    header_raw = f"{block_index}|{previous_hash}|{data_hash}|{sorted(meta.items())}".encode("utf-8")
    block_hash = hashlib.sha256(header_raw).hexdigest()

    return {
        "index": block_index,
        "previous_hash": previous_hash,
        "data_hash": data_hash,
        "block_hash": block_hash,
        "shape": list(data.shape),
        "dtype": str(data.dtype),
        "metadata": meta
    }

def verify_block_integrity(block: Dict[str, Any], data: np.ndarray) -> Tuple[bool, str]:
    actual_data_hash = hash_numpy_array(data)
    if actual_data_hash != block["data_hash"]:
        return False, f"Data hash mismatch! Expected {block['data_hash']}, got {actual_data_hash}"

    expected_header = f"{block['index']}|{block['previous_hash']}|{block['data_hash']}|{sorted(block['metadata'].items())}".encode("utf-8")
    if hashlib.sha256(expected_header).hexdigest() != block["block_hash"]:
        return False, "Block header tampering detected!"

    return True, "Integrity verified: Block and payload match perfectly."

# --- 4D, Signal & Numerical Processing ---

def normalize_quaternion(q: np.ndarray) -> np.ndarray:
    q = np.asarray(q, dtype=np.float64)
    norm = np.linalg.norm(q, axis=-1, keepdims=True)
    return q / np.where(norm == 0, 1.0, norm)

def quaternion_rotate_3d(vectors: np.ndarray, q: np.ndarray) -> np.ndarray:
    vectors = np.asarray(vectors, dtype=np.float64)
    if vectors.ndim == 1:
        vectors = vectors.reshape(1, 3)
    q_unit = normalize_quaternion(q)
    w, q_vec = q_unit[0], q_unit[1:]
    cross_qv = np.cross(q_vec, vectors)
    return vectors + 2.0 * np.cross(q_vec, cross_qv + w * vectors)

def rotation_matrix_4d(theta: float, plane: str = "xw") -> np.ndarray:
    cos_t, sin_t = np.cos(theta), np.sin(theta)
    mat = np.eye(4, dtype=np.float64)
    plane_map = {"xy": (0, 1), "xz": (0, 2), "xw": (0, 3), "yz": (1, 2), "yw": (1, 3), "zw": (2, 3)}
    if plane.lower() not in plane_map:
        raise ValueError(f"Unknown plane: {plane}")
    i, j = plane_map[plane.lower()]
    mat[i, i], mat[i, j], mat[j, i], mat[j, j] = cos_t, -sin_t, sin_t, cos_t
    return mat

def double_rotation_matrix_4d(theta1: float, theta2: float, plane_pair: str = "xw_yz") -> np.ndarray:
    pairs = {"xw_yz": ("xw", "yz"), "xy_zw": ("xy", "zw"), "xz_yw": ("xz", "yw")}
    if plane_pair.lower() not in pairs:
        raise ValueError(f"Unknown plane pair: {plane_pair}")
    p1, p2 = pairs[plane_pair.lower()]
    return np.matmul(rotation_matrix_4d(theta1, p1), rotation_matrix_4d(theta2, p2))

def isoclinic_rotation_matrix_4d(theta: float, plane_pair: str = "xw_yz", chirality: str = "left") -> np.ndarray:
    return double_rotation_matrix_4d(theta, theta if chirality == "left" else -theta, plane_pair)

def transform_4d_dataset(points: np.ndarray, theta: float, plane: str = "xw", double_theta: float = None) -> np.ndarray:
    points = np.asarray(points, dtype=np.float64)
    if double_theta is not None:
        mat = double_rotation_matrix_4d(theta, double_theta, plane)
    elif "_" in plane:
        mat = isoclinic_rotation_matrix_4d(theta, plane)
    else:
        mat = rotation_matrix_4d(theta, plane)
    return np.matmul(points, mat.T)

def calculate_shannon_entropy(data: np.ndarray, bins: int = 30, base: float = 2.0) -> float:
    arr = np.asarray(data, dtype=np.float64).flatten()
    if arr.size == 0: return 0.0
    counts, _ = np.histogram(arr, bins=bins)
    probs = counts / np.sum(counts)
    nonzero = probs[probs > 0]
    return float(-np.sum(nonzero * (np.log2(nonzero) if base == 2.0 else np.log(nonzero) / np.log(base))))

def compute_power_spectral_density(signal: np.ndarray, sampling_rate: float = 1.0) -> Tuple[np.ndarray, np.ndarray]:
    x = np.asarray(signal, dtype=np.float64).flatten()
    n = len(x)
    fft_vals = np.fft.rfft(x - np.mean(x))
    freqs = np.fft.rfftfreq(n, d=1.0 / sampling_rate)
    psd = (np.abs(fft_vals) ** 2) / (sampling_rate * n)
    if n % 2 == 0: psd[1:-1] *= 2.0
    else: psd[1:] *= 2.0
    return freqs, psd

def calculate_spectral_entropy(signal: np.ndarray, sampling_rate: float = 1.0) -> float:
    _, psd = compute_power_spectral_density(signal, sampling_rate)
    tot = np.sum(psd)
    if tot == 0.0: return 0.0
    norm = psd / tot
    nz = norm[norm > 0]
    max_e = np.log2(len(psd))
    return float(-np.sum(nz * np.log2(nz)) / max_e) if max_e > 0 else 0.0

def process_vector_data(input_array: np.ndarray, scale_factor: float = 1.0) -> np.ndarray:
    arr = np.asarray(input_array, dtype=np.float64)
    return (arr * scale_factor) - np.mean(arr)
