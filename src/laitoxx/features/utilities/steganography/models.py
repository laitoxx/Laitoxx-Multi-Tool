"""ST3GG container format and configuration value objects."""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from enum import Enum, IntEnum

import numpy as np

# ============== CONSTANTS ==============

MAGIC_BYTES = b"STEG"  # Magic signature
FORMAT_VERSION = 3  # Current format version
HEADER_SIZE = 32  # Fixed header size in bytes


class Channel(IntEnum):
    """Color channels - IntEnum for direct numpy indexing"""

    R = 0
    G = 1
    B = 2
    A = 3


class EncodingStrategy(Enum):
    """Different strategies for embedding data"""

    SEQUENTIAL = "sequential"  # Fill pixels in order
    INTERLEAVED = "interleaved"  # Cycle through channels per pixel
    SPREAD = "spread"  # Spread across image evenly
    RANDOMIZED = "randomized"  # Pseudo-random order (seeded)


# ============== CONFIGURATION ==============


@dataclass
class StegConfig:
    """Configuration for steganography operations"""

    channels: list[Channel] = field(default_factory=lambda: [Channel.R, Channel.G, Channel.B])
    bits_per_channel: int = 1
    bit_offset: int = 0
    use_compression: bool = True
    strategy: EncodingStrategy = EncodingStrategy.INTERLEAVED
    seed: int | None = None  # For randomized strategy

    @property
    def bits_per_pixel(self) -> int:
        return len(self.channels) * self.bits_per_channel

    @property
    def channel_indices(self) -> np.ndarray:
        return np.array([c.value for c in self.channels], dtype=np.uint8)

    def to_bytes(self) -> bytes:
        """Serialize config to bytes for header"""
        flags = 0
        flags |= (1 << 0) if self.use_compression else 0
        flags |= (self.strategy.value == "interleaved") << 1
        flags |= (self.strategy.value == "spread") << 2
        flags |= (self.strategy.value == "randomized") << 3

        channel_mask = sum(1 << c.value for c in self.channels)

        return struct.pack(">BBBB I", channel_mask, self.bits_per_channel, self.bit_offset, flags, self.seed or 0)

    @classmethod
    def from_bytes(cls, data: bytes) -> StegConfig:
        """Deserialize config from bytes"""
        channel_mask, bits_per_ch, bit_offset, flags, seed = struct.unpack(">BBBB I", data)

        channels = [Channel(i) for i in range(4) if channel_mask & (1 << i)]
        use_compression = bool(flags & 1)

        if flags & (1 << 3):
            strategy = EncodingStrategy.RANDOMIZED
        elif flags & (1 << 2):
            strategy = EncodingStrategy.SPREAD
        elif flags & (1 << 1):
            strategy = EncodingStrategy.INTERLEAVED
        else:
            strategy = EncodingStrategy.SEQUENTIAL

        return cls(
            channels=channels,
            bits_per_channel=bits_per_ch,
            bit_offset=bit_offset,
            use_compression=use_compression,
            strategy=strategy,
            seed=seed if seed else None,
        )


# Channel presets
CHANNEL_PRESETS = {
    "R": [Channel.R],
    "G": [Channel.G],
    "B": [Channel.B],
    "A": [Channel.A],
    "RG": [Channel.R, Channel.G],
    "RB": [Channel.R, Channel.B],
    "RA": [Channel.R, Channel.A],
    "GB": [Channel.G, Channel.B],
    "GA": [Channel.G, Channel.A],
    "BA": [Channel.B, Channel.A],
    "RGB": [Channel.R, Channel.G, Channel.B],
    "RGA": [Channel.R, Channel.G, Channel.A],
    "RBA": [Channel.R, Channel.B, Channel.A],
    "GBA": [Channel.G, Channel.B, Channel.A],
    "RGBA": [Channel.R, Channel.G, Channel.B, Channel.A],
}


def get_channel_preset(name: str) -> list[Channel]:
    """Get channel list from preset name"""
    return CHANNEL_PRESETS.get(name.upper(), [Channel.R, Channel.G, Channel.B])


def derive_magic(password: str) -> bytes:
    """Derive 4-byte magic from password using HMAC-SHA256.

    When a password is provided, the STEG header magic is derived from
    the password instead of using the fixed 'STEG' bytes. This means
    the header is undetectable without the password - no fixed signature
    to scan for.
    """
    import hmac

    return hmac.new(password.encode("utf-8"), b"ST3GG-MAGIC-V3", "sha256").digest()[:4]


# ============== HEADER FORMAT ==============
"""
Header Format (32 bytes):
  [0:4]   - Magic bytes: 'STEG'
  [4:5]   - Version: uint8
  [5:6]   - Channel mask: uint8 (bit flags for R,G,B,A)
  [6:7]   - Bits per channel: uint8
  [7:8]   - Bit offset: uint8
  [8:9]   - Flags: uint8 (compression, strategy bits)
  [9:12]  - Reserved: 3 bytes
  [12:16] - Seed: uint32 (for randomized strategy)
  [16:20] - Payload length: uint32
  [20:24] - Original length: uint32 (before compression)
  [24:28] - CRC32: uint32
  [28:32] - Reserved: 4 bytes
"""


@dataclass
class StegHeader:
    """Header for encoded data"""

    version: int = FORMAT_VERSION
    config: StegConfig = field(default_factory=StegConfig)
    payload_length: int = 0
    original_length: int = 0
    crc32: int = 0

    def to_bytes(self, password: str | None = None) -> bytes:
        """Serialize header to 32 bytes.

        If password is provided, the magic bytes are derived from the password
        using HMAC-SHA256, making the header undetectable without the password.
        """
        config_bytes = self.config.to_bytes()

        header = bytearray(HEADER_SIZE)
        header[0:4] = derive_magic(password) if password else MAGIC_BYTES
        header[4] = self.version
        header[5:13] = config_bytes
        struct.pack_into(">I", header, 16, self.payload_length)
        struct.pack_into(">I", header, 20, self.original_length)
        struct.pack_into(">I", header, 24, self.crc32)

        return bytes(header)

    @classmethod
    def from_bytes(cls, data: bytes, password: str | None = None) -> StegHeader:
        """Deserialize header from bytes.

        If password is provided, validates against password-derived magic.
        Otherwise validates against the fixed 'STEG' magic bytes.
        """
        if len(data) < HEADER_SIZE:
            raise ValueError(f"Header too short: {len(data)} < {HEADER_SIZE}")

        magic = data[0:4]
        expected = derive_magic(password) if password else MAGIC_BYTES
        if magic != expected:
            raise ValueError(f"Invalid magic bytes: {magic!r} != {expected!r}")

        version = data[4]
        if version > FORMAT_VERSION:
            raise ValueError(f"Unsupported version: {version} > {FORMAT_VERSION}")

        config = StegConfig.from_bytes(data[5:13])
        payload_length = struct.unpack(">I", data[16:20])[0]
        original_length = struct.unpack(">I", data[20:24])[0]
        crc32 = struct.unpack(">I", data[24:28])[0]

        return cls(
            version=version, config=config, payload_length=payload_length, original_length=original_length, crc32=crc32
        )
