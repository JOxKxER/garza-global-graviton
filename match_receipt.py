"""
match_receipt.py - Cryptographic Merkle Telemetry Engine & Hit-Reg Verification
Generates SHA-256 Merkle Trees and detailed spatial tick telemetry for hit-reg inspection.
"""

import hashlib
import json
import time
import math
from datetime import datetime
from typing import List, Dict, Any

def sha256_hash(data: str) -> str:
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

class MerkleTelemetryTree:
    def __init__(self, leaf_hashes: List[str]):
        if not leaf_hashes:
            raise ValueError("Leaf hashes list cannot be empty.")
        self.leaf_hashes = leaf_hashes
        self.root_hash = self._build_tree(leaf_hashes)

    def _build_tree(self, hashes: List[str]) -> str:
        if len(hashes) == 1:
            return hashes[0]

        next_level = []
        for i in range(0, len(hashes), 2):
            left = hashes[i]
            right = hashes[i + 1] if i + 1 < len(hashes) else left
            next_level.append(sha256_hash(left + right))

        return self._build_tree(next_level)

class MatchReceiptGenerator:
    def __init__(self, match_id: str, server_id: str, tickrate: int = 128):
        self.match_id = match_id
        self.server_id = server_id
        self.tickrate = tickrate
        self.ticks: List[Dict[str, Any]] = []
        self.leaf_hashes: List[str] = []

    def record_tick(self, tick_index: int, player_states: List[Dict[str, Any]], server_authoritative: bool = True):
        tick_payload = {
            "tick": tick_index,
            "timestamp_ms": int(time.time() * 1000),
            "authoritative": server_authoritative,
            "players": sorted(player_states, key=lambda x: x["player_id"])
        }
        canonical_str = json.dumps(tick_payload, sort_keys=True)
        tick_hash = sha256_hash(canonical_str)

        self.ticks.append(tick_payload)
        self.leaf_hashes.append(tick_hash)

    def finalize_match(self, winner_team: str, players_roster: List[str], anti_cheat_clean: bool = True) -> Dict[str, Any]:
        tree = MerkleTelemetryTree(self.leaf_hashes)
        return {
            "version": "1.2-merkle-spatial",
            "match_id": self.match_id,
            "server_id": self.server_id,
            "finalized_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tickrate_hz": self.tickrate,
            "total_ticks_analyzed": len(self.ticks),
            "roster": sorted(players_roster),
            "match_outcome": {
                "winner": winner_team,
                "fair_play_certified": anti_cheat_clean,
                "anomalies_flagged": 0 if anti_cheat_clean else 1
            },
            "spatial_telemetry": self.ticks,
            "cryptography": {
                "hash_algorithm": "SHA-256",
                "merkle_root": tree.root_hash,
                "first_tick_hash": self.leaf_hashes[0],
                "last_tick_hash": self.leaf_hashes[-1]
            }
        }

def verify_match_receipt(ticks: List[Dict[str, Any]], expected_merkle_root: str) -> bool:
    recomputed_leaves = []
    for tick_payload in ticks:
        canonical_str = json.dumps(tick_payload, sort_keys=True)
        recomputed_leaves.append(sha256_hash(canonical_str))

    tree = MerkleTelemetryTree(recomputed_leaves)
    return tree.root_hash == expected_merkle_root