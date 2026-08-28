"""CNC air-gapped job attestation toolkit.

Proves to enterprise buyers that a submitted G-code/toolpath job ran on an
isolated CNC controller (e.g. Shapeoko Pro, Nomad 3) without network/radio
activity and without the toolpath being altered -- verifiable offline with
only verify_cnc_client.py, a pinned controller public key, and the bundle.

Standalone by design: no dependency on the unrelated airgap_attestation
(software air-gap) product line, even though the underlying Merkle/signing
cryptography is conceptually the same.
"""

from .controller_quote import CncAttestationBundle, ControllerStateQuote
from .gcode_merkle import GCodeAuditManifest, GCodeExecutionEvent, MerkleTree

__all__ = [
    "MerkleTree",
    "GCodeExecutionEvent",
    "GCodeAuditManifest",
    "ControllerStateQuote",
    "CncAttestationBundle",
]
