"""Non-block integer-range arithmetic coding for near-entropy compression.

Tactical use: unlike block codes (Huffman, fixed-width symbols),
arithmetic coding represents an entire payload as a single refined
sub-interval of [0, 1), letting the encoded length approach the
theoretical Shannon entropy limit even when per-symbol probabilities are
not exact powers of two. This is the classic Witten-Neal-Cleary integer
implementation (CACM, 1987) -- a real, well-defined coding-theory
algorithm, not a heuristic.
"""

from __future__ import annotations

from collections import Counter

import numpy as np

CODE_BITS = 32
TOP_VALUE = (1 << CODE_BITS) - 1
FIRST_QUARTER = (TOP_VALUE // 4) + 1
HALF = 2 * FIRST_QUARTER
THIRD_QUARTER = 3 * FIRST_QUARTER


class _BitWriter:
    """Accumulates output bits, including pending E3 underflow bits."""

    def __init__(self) -> None:
        self.bits: list[int] = []
        self.pending_bits = 0

    def output_bit(self, bit: int) -> None:
        """Emit one bit, followed by any pending complementary bits."""
        self.bits.append(bit)
        opposite = 1 - bit
        self.bits.extend([opposite] * self.pending_bits)
        self.pending_bits = 0

    def to_bytes(self) -> bytes:
        """Pack the accumulated bitstream into a byte string."""
        return np.packbits(np.array(self.bits, dtype=np.uint8)).tobytes()


class _BitReader:
    """Reads bits from an encoded stream, padding with zeros past the end."""

    def __init__(self, data: bytes) -> None:
        self._bits = np.unpackbits(np.frombuffer(data, dtype=np.uint8))
        self._cursor = 0

    def next_bit(self) -> int:
        """Return the next bit, or 0 once the real bitstream is exhausted."""
        if self._cursor < self._bits.size:
            bit = int(self._bits[self._cursor])
            self._cursor += 1
            return bit
        return 0


def _build_cumulative_frequencies(module_payload: bytes) -> np.ndarray:
    """Build a length-257 cumulative frequency table with +1 smoothing.

    Additive smoothing guarantees every one of the 256 possible byte
    values has nonzero probability, so the model never fails on a symbol
    that happened not to appear in this particular payload.
    """
    counts = Counter(module_payload)
    frequencies = np.ones(256, dtype=np.int64)
    for symbol, count in counts.items():
        frequencies[symbol] += count

    total_frequency = int(np.sum(frequencies))
    if total_frequency >= FIRST_QUARTER:
        raise ValueError(
            "payload too large for this precision; increase CODE_BITS"
        )

    cumulative_frequencies = np.zeros(257, dtype=np.int64)
    cumulative_frequencies[1:] = np.cumsum(frequencies)
    return cumulative_frequencies


class ArithmeticCoder:
    """Encodes/decodes a byte payload via integer-range arithmetic coding."""

    @staticmethod
    def encode(module_payload: bytes) -> tuple[bytes, np.ndarray, int]:
        """Encode a payload, returning (encoded_bytes, cum_freq, num_symbols).

        Tactical advantage: the returned cumulative-frequency table is the
        entire decoder "model" -- a small, explicit header rather than a
        hidden adaptive state -- so any node can decode independently of
        encoder history.
        """
        cumulative_frequencies = _build_cumulative_frequencies(module_payload)
        total = int(cumulative_frequencies[-1])

        low, high = 0, TOP_VALUE
        writer = _BitWriter()

        for byte in module_payload:
            span = high - low + 1
            high = (
                low
                + (span * int(cumulative_frequencies[byte + 1])) // total
                - 1
            )
            low = low + (span * int(cumulative_frequencies[byte])) // total

            while True:
                if high < HALF:
                    writer.output_bit(0)
                elif low >= HALF:
                    writer.output_bit(1)
                    low -= HALF
                    high -= HALF
                elif low >= FIRST_QUARTER and high < THIRD_QUARTER:
                    writer.pending_bits += 1
                    low -= FIRST_QUARTER
                    high -= FIRST_QUARTER
                else:
                    break
                low *= 2
                high = 2 * high + 1

        writer.pending_bits += 1
        writer.output_bit(0 if low < FIRST_QUARTER else 1)

        return writer.to_bytes(), cumulative_frequencies, len(module_payload)

    @staticmethod
    def decode(
        encoded_stream: bytes,
        cumulative_frequencies: np.ndarray,
        num_symbols: int,
    ) -> bytes:
        """Decode a payload from its encoded stream and frequency model.

        Tactical advantage: reconstructs the exact original byte sequence
        with no loss, using only the compact model shipped alongside the
        encoded stream.
        """
        total = int(cumulative_frequencies[-1])
        reader = _BitReader(encoded_stream)

        value = 0
        for _ in range(CODE_BITS):
            value = 2 * value + reader.next_bit()

        low, high = 0, TOP_VALUE
        decoded_payload = bytearray()

        for _ in range(num_symbols):
            span = high - low + 1
            scaled_value = ((value - low + 1) * total - 1) // span
            symbol = (
                int(
                    np.searchsorted(
                        cumulative_frequencies, scaled_value, side="right"
                    )
                )
                - 1
            )
            decoded_payload.append(symbol)

            high = (
                low
                + (span * int(cumulative_frequencies[symbol + 1])) // total
                - 1
            )
            low = (
                low
                + (span * int(cumulative_frequencies[symbol])) // total
            )

            while True:
                if high < HALF:
                    pass
                elif low >= HALF:
                    value -= HALF
                    low -= HALF
                    high -= HALF
                elif low >= FIRST_QUARTER and high < THIRD_QUARTER:
                    value -= FIRST_QUARTER
                    low -= FIRST_QUARTER
                    high -= FIRST_QUARTER
                else:
                    break
                low *= 2
                high = 2 * high + 1
                value = 2 * value + reader.next_bit()

        return bytes(decoded_payload)


if __name__ == "__main__":
    payload = (
        b"the quick brown fox jumps over the lazy dog " * 20
        + b"\x00\x00\x00low-entropy-tail\x00\x00\x00"
    )

    encoded, cumulative, demo_num_symbols = ArithmeticCoder.encode(payload)
    decoded = ArithmeticCoder.decode(encoded, cumulative, demo_num_symbols)

    assert decoded == payload, "Arithmetic coding round-trip failed."

    raw_size = len(payload)
    encoded_size = len(encoded)
    print("ArithmeticCoder self-test passed.")
    print(f"Raw payload bytes: {raw_size}")
    print(f"Encoded bytes: {encoded_size}")
    print(f"Compression ratio: {1.0 - (encoded_size / raw_size):.2%}")
