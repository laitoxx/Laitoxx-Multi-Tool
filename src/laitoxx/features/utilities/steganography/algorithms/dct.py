try:
    import cv2
except ImportError:
    cv2 = None
import numpy as np


def encode_dct(image_path: str, data: bytes, output_path: str, robustness: str = "medium"):
    if cv2 is None:
        raise RuntimeError("OpenCV is required for DCT steganography")
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError("Image not found")

    strength_map = {"low": 10, "medium": 25, "high": 50}
    strength = strength_map.get(robustness.lower(), 25)

    header = b"DCTS" + bytes([strength]) + len(data).to_bytes(4, "big")
    payload = header + data

    bits = np.unpackbits(np.frombuffer(payload, dtype=np.uint8))

    H, W, _ = img.shape
    blocks_h, blocks_w = H // 8, W // 8
    capacity = blocks_h * blocks_w

    if len(bits) > capacity:
        raise ValueError(f"Capacity exceeded! Need {len(bits)} bits, but image only fits {capacity} bits.")

    img_float = img.astype(np.float32)

    lum = 0.114 * img_float[:, :, 0] + 0.587 * img_float[:, :, 1] + 0.299 * img_float[:, :, 2]

    bit_idx = 0
    total_bits = len(bits)

    for y in range(blocks_h):
        for x in range(blocks_w):
            if bit_idx >= total_bits:
                break

            y_start, y_end = y * 8, y * 8 + 8
            x_start, x_end = x * 8, x * 8 + 8

            block = lum[y_start:y_end, x_start:x_end]

            dct_block = cv2.dct(block)

            coeff = dct_block[0, 1]
            q = np.floor(coeff / strength)
            bit = bits[bit_idx]

            dct_block[0, 1] = (q + (0.75 if bit else 0.25)) * strength
            bit_idx += 1

            idct_block = cv2.idct(dct_block)

            old_lum = block
            new_lum = np.clip(idct_block, 0, 255)

            ratio = np.ones_like(old_lum)
            mask = old_lum > 0
            ratio[mask] = new_lum[mask] / old_lum[mask]

            for c in range(3):
                img_float[y_start:y_end, x_start:x_end, c] = np.clip(
                    np.round(img_float[y_start:y_end, x_start:x_end, c] * ratio), 0, 255
                )

    cv2.imwrite(output_path, img_float.astype(np.uint8))


def decode_dct(image_path: str) -> bytes:
    if cv2 is None:
        raise RuntimeError("OpenCV is required for DCT steganography")
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError("Image not found")

    img_float = img.astype(np.float32)
    lum = 0.114 * img_float[:, :, 0] + 0.587 * img_float[:, :, 1] + 0.299 * img_float[:, :, 2]

    H, W, _ = img.shape
    blocks_h, blocks_w = H // 8, W // 8

    coefficients = []

    for y in range(blocks_h):
        for x in range(blocks_w):
            y_start, y_end = y * 8, y * 8 + 8
            x_start, x_end = x * 8, x * 8 + 8

            block = lum[y_start:y_end, x_start:x_end]
            dct_block = cv2.dct(block)
            coefficients.append(dct_block[0, 1])

    for strength in [10, 25, 50]:
        bits = []
        for coeff in coefficients:
            q = np.floor(coeff / strength)
            remainder = coeff - (q * strength)
            bits.append(1 if remainder >= (strength / 2) else 0)

        byte_arr = np.packbits(bits)

        if len(byte_arr) >= 9:
            if tuple(byte_arr[:4]) == (0x44, 0x43, 0x54, 0x53):
                header_strength = byte_arr[4]
                if header_strength == strength:
                    data_len = int.from_bytes(byte_arr[5:9], "big")
                    if data_len <= len(byte_arr) - 9:
                        return bytes(byte_arr[9 : 9 + data_len])

    raise ValueError("No valid DCT steganography payload found.")
