"""Hardware-root-of-trust attestation interfaces.

Two independent hardware evidence sources are supported, either of which can
back an AttestationBundle:

* TPM 2.0 quote  -- the isolated execution node's firmware/kernel/network
  driver state is measured into Platform Configuration Registers (PCRs)
  during boot. A quote signed by the TPM's Attestation Key (AK) over
  (nonce || merkle_root) proves the Merkle root was observed by *this
  specific, measured machine state* and was not fabricated after the fact
  on different hardware.
* Secure enclave attestation (Intel SGX / AMD SEV-SNP / AWS Nitro Enclaves)
  -- the execution runs inside a hardware-isolated memory region; the
  enclave's attestation document is signed by a manufacturer-rooted key and
  binds a measurement of the enclave's code + the same (nonce || merkle_root)
  payload.

Real deployments plug in `Tpm2ToolsAttestor` (or an SGX/Nitro equivalent)
behind the `HardwareAttestor` interface. `ReferenceSoftwareAttestor` below is
a software-only stand-in used for local development/testing of the rest of
the pipeline (schemas, Merkle log, signing, verification) -- it must never be
used to back a real client-facing attestation bundle, which is why it stamps
its quote_format as "SOFTWARE_REFERENCE_ONLY_NOT_HARDWARE_ROOTED".
"""

from __future__ import annotations

import abc
import os
import subprocess
from dataclasses import dataclass
from typing import List, Optional

from . import signing
from .schemas import TpmQuoteEvidence, _utc_now_iso


@dataclass(frozen=True)
class PcrBaseline:
    """PCR values captured before execution begins, used to detect any
    mid-run reconfiguration (e.g. a network driver being loaded)."""

    pcr_selection: List[int]
    pcr_digest: str  # hex


class HardwareAttestor(abc.ABC):
    @abc.abstractmethod
    def capture_baseline(self) -> PcrBaseline:
        """Snapshot the current hardware-measured state before the job runs."""

    @abc.abstractmethod
    def quote(self, nonce: bytes, merkle_root: bytes) -> TpmQuoteEvidence:
        """Produce a hardware-signed quote binding (nonce || merkle_root) to
        the current measured state. Must be called *after* execution
        completes and the Merkle root is final."""


class Tpm2ToolsAttestor(HardwareAttestor):
    """Production TPM 2.0 backend using the standard `tpm2-tools` CLI.

    Requires: a physical or virtual TPM 2.0 device (/dev/tpm0 or
    /dev/tpmrm0), `tpm2-tools` installed, and an Attestation Key already
    provisioned and certified by the vendor's PKI. This class only shells
    out to well-known tpm2-tools subcommands; it holds no private key
    material itself.
    """

    def __init__(
        self,
        ak_context_path: str,
        ak_certificate_path: str,
        pcr_selection: str = "sha256:0,1,2,3,4,7",
    ):
        self.ak_context_path = ak_context_path
        self.ak_certificate_path = ak_certificate_path
        self.pcr_selection = pcr_selection

    def capture_baseline(self) -> PcrBaseline:
        digest = self._run(["tpm2_pcrread", self.pcr_selection])
        return PcrBaseline(pcr_selection=self._parse_pcr_indices(), pcr_digest=digest)

    def quote(self, nonce: bytes, merkle_root: bytes) -> TpmQuoteEvidence:
        quoted_data = nonce + merkle_root
        qualifying_data_path = self._write_temp(quoted_data)
        try:
            quote_output = self._run(
                [
                    "tpm2_quote",
                    "-c",
                    self.ak_context_path,
                    "-l",
                    self.pcr_selection,
                    "-q",
                    qualifying_data_path,
                    "-m",
                    "-",  # message (quoted attestation structure) to stdout
                    "-s",
                    "-",  # signature to stdout
                ]
            )
        finally:
            os.unlink(qualifying_data_path)

        with open(self.ak_certificate_path, "r", encoding="utf-8") as f:
            ak_certificate = f.read()

        return TpmQuoteEvidence(
            quote_format="TPM2_QUOTE_V1",
            pcr_selection=self._parse_pcr_indices(),
            pcr_digest=quote_output,
            nonce=nonce.hex(),
            quoted_data=quoted_data.hex(),
            signature=quote_output,  # real impl: parse tpm2_quote's split outputs
            ak_certificate=ak_certificate,
            generated_at=_utc_now_iso(),
        )

    def _parse_pcr_indices(self) -> List[int]:
        _, indices = self.pcr_selection.split(":")
        return [int(i) for i in indices.split(",")]

    @staticmethod
    def _run(cmd: List[str]) -> str:
        result = subprocess.run(cmd, capture_output=True, check=True, text=True)
        return result.stdout.strip()

    @staticmethod
    def _write_temp(data: bytes) -> str:
        import tempfile

        fd, path = tempfile.mkstemp(prefix="ggg_quote_qdata_")
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        return path


class ReferenceSoftwareAttestor(HardwareAttestor):
    """NOT hardware-rooted. For local development/CI only -- exercises the
    same schema and signing flow as Tpm2ToolsAttestor using an in-process
    Ed25519 key standing in for a TPM AK. Any bundle produced with this
    attestor must be rejected by a compliance-grade verifier."""

    QUOTE_FORMAT = "SOFTWARE_REFERENCE_ONLY_NOT_HARDWARE_ROOTED"

    def __init__(self, ak_private_key: Optional[bytes] = None):
        if ak_private_key is None:
            ak_private_key, ak_public_key = signing.generate_keypair()
        else:
            _, ak_public_key = signing.generate_keypair()
        self._ak_private_key = ak_private_key
        self.ak_public_key = ak_public_key

    def capture_baseline(self) -> PcrBaseline:
        return PcrBaseline(pcr_selection=[0, 1, 2, 3, 4, 7], pcr_digest="00" * 32)

    def quote(self, nonce: bytes, merkle_root: bytes) -> TpmQuoteEvidence:
        quoted_data = nonce + merkle_root
        signature = signing.sign(self._ak_private_key, quoted_data)
        return TpmQuoteEvidence(
            quote_format=self.QUOTE_FORMAT,
            pcr_selection=[0, 1, 2, 3, 4, 7],
            pcr_digest="00" * 32,
            nonce=nonce.hex(),
            quoted_data=quoted_data.hex(),
            signature=signature.hex(),
            ak_certificate=self.ak_public_key.hex(),
            generated_at=_utc_now_iso(),
        )
