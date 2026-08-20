"""Convenience API for configuring and encoding text."""

from __future__ import annotations

from PIL import Image

from .decoder import decode
from .encoder import encode
from .models import EncodingStrategy, StegConfig, get_channel_preset


def encode_text(image: Image.Image, text: str, config: StegConfig, output_path: str | None = None) -> Image.Image:
    """Encode text string into image"""
    return encode(image, text.encode("utf-8"), config, output_path)


def decode_text(image: Image.Image, config: StegConfig | None = None) -> str:
    """Decode text string from image"""
    data = decode(image, config)
    return data.decode("utf-8")


def create_config(
    channels: str = "RGB",
    bits: int = 1,
    compress: bool = True,
    strategy: str = "interleaved",
    bit_offset: int = 0,
    seed: int | None = None,
) -> StegConfig:
    """
    Create a StegConfig with convenient parameters.

    Args:
        channels: Channel preset name (R, G, B, A, RGB, RGBA, etc.)
        bits: Bits per channel (1-8)
        compress: Whether to compress data
        strategy: Encoding strategy ('sequential', 'interleaved', 'spread', 'randomized')
        bit_offset: Bit position offset (0 = LSB)
        seed: Random seed for randomized strategy

    Returns:
        StegConfig instance
    """
    strategy_map = {
        "sequential": EncodingStrategy.SEQUENTIAL,
        "interleaved": EncodingStrategy.INTERLEAVED,
        "spread": EncodingStrategy.SPREAD,
        "randomized": EncodingStrategy.RANDOMIZED,
    }

    return StegConfig(
        channels=get_channel_preset(channels),
        bits_per_channel=max(1, min(8, bits)),
        bit_offset=max(0, min(7, bit_offset)),
        use_compression=compress,
        strategy=strategy_map.get(strategy.lower(), EncodingStrategy.INTERLEAVED),
        seed=seed,
    )
