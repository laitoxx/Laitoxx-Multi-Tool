try:
    from .chroma import ChromaSteganography
    from .dct import decode_dct, encode_dct
except ModuleNotFoundError as exc:
    if exc.name != "cv2":
        raise

    _opencv_error = exc
    ChromaSteganography = None

    def _opencv_required(*_args, **_kwargs):
        raise RuntimeError("OpenCV is required for DCT and chroma steganography") from _opencv_error

    encode_dct = decode_dct = _opencv_required
from .f5 import F5Stego
from .metadata import decode_pngchunk, decode_textoverlay, encode_pngchunk, encode_textoverlay
from .palette import decode_palette, encode_palette
from .pvd import decode_pvd, encode_pvd
from .spread import decode_spread, encode_spread

__all__ = [
    "encode_pvd",
    "decode_pvd",
    "F5Stego",
    "ChromaSteganography",
    "encode_dct",
    "decode_dct",
    "encode_palette",
    "decode_palette",
    "encode_pngchunk",
    "decode_pngchunk",
    "encode_textoverlay",
    "decode_textoverlay",
    "encode_spread",
    "decode_spread",
]
