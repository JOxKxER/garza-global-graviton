"""Hamming(7,4) forward error correction: bitwise encode and syndrome decode.

Tactical use: embeds 3 parity bits into every 4 data bits so a single
flipped bit anywhere in a transmitted module stream is detected AND
corrected in place, without a retransmission round-trip. This is the
standard, textbook Hamming(7,4) single-error-correcting code -- a real,
well-defined coding-theory primitive, not a heuristic.
"""

from __future__ import annotations

import numpy as np

# Systematic generator matrix G = [I4 | P]: data bits pass through
# unmodified in positions 0-3, parity bits occupy positions 4-6.
GENERATOR_MATRIX = np.array(
    [
        [1, 0, 0, 0, 0, 1, 1],
        [0, 1, 0, 0, 1, 0, 1],
        [0, 0, 1, 0, 1, 1, 0],
        [0, 0, 0, 1, 1, 1, 1],
    ],
    dtype=np.uint8,
)

# Parity-check matrix H = [P^T | I3]; H @ G^T == 0 (mod 2).
PARITY_CHECK_MATRIX = np.array(
    [
        [0, 1, 1, 1, 1, 0, 0],
        [1, 0, 1, 1, 0, 1, 0],
        [1, 1, 0, 1, 0, 0, 1],
    ],
    dtype=np.uint8,
)


def _build_syndrome_table() -> dict[tuple[int, ...], int]:
    """Map each possible 3-bit syndrome to the codeword bit index it flags."""
    table: dict[tuple[int, ...], int] = {}
    for bit_index in range(7):
        column = tuple(
            int(value) for value in PARITY_CHECK_MATRIX[:, bit_index]
        )
        table[column] = bit_index
    return table


class HammingFEC:
    """Encodes 4-bit nibbles to 7-bit codewords, corrects single-bit errors."""

    _SYNDROME_TABLE = _build_syndrome_table()

    @staticmethod
    def _nibble_to_bits(nibble: int) -> np.ndarray:
        """Convert a 4-bit integer (0-15) into an MSB-first bit array."""
        if not 0 <= nibble <= 15:
            raise ValueError("nibble must be in range 0-15")
        return np.array(
            [(nibble >> shift) & 1 for shift in (3, 2, 1, 0)], dtype=np.uint8
        )

    @staticmethod
    def _bits_to_nibble(nibble_bits: np.ndarray) -> int:
        """Convert an MSB-first 4-bit array back into an integer 0-15."""
        weights = np.array([8, 4, 2, 1], dtype=np.int64)
        return int(np.dot(nibble_bits.astype(np.int64), weights))

    @classmethod
    def encode_nibble(cls, nibble: int) -> np.ndarray:
        """Encode a 4-bit nibble into its 7-bit Hamming(7,4) codeword.

        Tactical advantage: a single matrix-vector product over GF(2)
        produces a codeword that can survive any single bit flip in
        transit, with no external parity channel required.
        """
        data_bits = cls._nibble_to_bits(nibble)
        codeword = (data_bits @ GENERATOR_MATRIX) % 2
        return codeword.astype(np.uint8)

    @classmethod
    def decode_codeword(cls, codeword) -> tuple[np.ndarray, int, int]:
        """Correct at most one bit flip and recover the original nibble.

        Returns the corrected 7-bit codeword, the decoded nibble, and the
        corrected bit index (-1 if the codeword was already error-free).

        Tactical advantage: the syndrome lookup is an O(1) dictionary hit
        per codeword, so error correction never triggers a retransmission
        request even under active bit-flip noise.
        """
        received = np.asarray(codeword, dtype=np.uint8) % 2
        if received.shape != (7,):
            raise ValueError("codeword must contain exactly 7 bits")

        syndrome = tuple(
            int(value) for value in (PARITY_CHECK_MATRIX @ received) % 2
        )
        corrected = received.copy()
        error_index = -1
        if syndrome != (0, 0, 0):
            error_index = cls._SYNDROME_TABLE.get(syndrome, -1)
            if error_index != -1:
                corrected[error_index] ^= 1

        nibble = cls._bits_to_nibble(corrected[:4])
        return corrected, nibble, error_index

    @classmethod
    def encode_bytes(cls, module_payload: bytes) -> bytes:
        """Encode a byte payload into a Hamming(7,4)-protected bitstream.

        Tactical advantage: every byte becomes two independently
        correctable 7-bit codewords, so a single flipped bit anywhere in
        the transmitted stream never corrupts more than the nibble it
        occurred in.
        """
        bit_buffer: list[int] = []
        for byte in module_payload:
            for nibble in ((byte >> 4) & 0x0F, byte & 0x0F):
                codeword = cls.encode_nibble(nibble)
                bit_buffer.extend(int(bit) for bit in codeword)
        return np.packbits(np.array(bit_buffer, dtype=np.uint8)).tobytes()

    @classmethod
    def decode_bytes(
        cls, encoded_stream: bytes, num_nibbles: int
    ) -> tuple[bytes, int]:
        """Decode a Hamming(7,4) bitstream back into the original payload.

        Tactical advantage: reports exactly how many bit errors were
        corrected, giving an operator a live channel-quality signal
        alongside the recovered data.
        """
        total_bits = num_nibbles * 7
        bits = np.unpackbits(
            np.frombuffer(encoded_stream, dtype=np.uint8)
        )[:total_bits]

        nibbles: list[int] = []
        corrected_count = 0
        for index in range(num_nibbles):
            chunk = bits[index * 7:(index + 1) * 7]
            _, nibble, error_index = cls.decode_codeword(chunk)
            if error_index != -1:
                corrected_count += 1
            nibbles.append(nibble)

        data_bytes = bytearray()
        for index in range(0, len(nibbles), 2):
            high_nibble = nibbles[index]
            low_nibble = nibbles[index + 1] if index + 1 < len(nibbles) else 0
            data_bytes.append((high_nibble << 4) | low_nibble)
        return bytes(data_bytes), corrected_count

    @staticmethod
    def flip_bit(codeword: np.ndarray, bit_index: int) -> np.ndarray:
        """Flip a single bit in a codeword to simulate transmission noise."""
        corrupted = np.asarray(codeword, dtype=np.uint8).copy()
        corrupted[bit_index] ^= 1
        return corrupted


if __name__ == "__main__":
    payload = b"GGG-EDGE-MODULE"
    encoded = HammingFEC.encode_bytes(payload)
    demo_num_nibbles = len(payload) * 2

    decoded_clean, corrections_clean = HammingFEC.decode_bytes(
        encoded, demo_num_nibbles
    )
    assert decoded_clean == payload, "Clean round-trip decode failed."
    assert corrections_clean == 0, "Unexpected correction on clean channel."

    demo_bits = np.unpackbits(np.frombuffer(encoded, dtype=np.uint8))
    noisy_bits = demo_bits.copy()
    for codeword_index in range(0, len(noisy_bits), 7):
        noisy_bits[codeword_index] ^= 1  # flip one bit per 7-bit codeword
    noisy_encoded = np.packbits(noisy_bits).tobytes()

    decoded_noisy, corrections_noisy = HammingFEC.decode_bytes(
        noisy_encoded, demo_num_nibbles
    )
    assert decoded_noisy == payload, "Noisy round-trip decode failed."
    assert corrections_noisy == demo_num_nibbles, "Not all errors fixed."

    print("HammingFEC self-test passed.")
    print(f"Payload: {payload!r}")
    encoded_len, corrected_len = len(encoded), len(noisy_encoded)
    print(f"Encoded bytes: {encoded_len} -> corrected bytes: {corrected_len}")
    print(f"Bit errors injected and corrected: {corrections_noisy}")
