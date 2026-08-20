try:
    import cv2
except ImportError:
    cv2 = None


class ChromaSteganography:
    def __init__(self):
        if cv2 is None:
            raise RuntimeError("OpenCV is required for chroma steganography")
        self.DELIMITER = b"====EOF===="

    def _rgb_to_ycbcr(self, r, g, b):
        y = int(0.299 * r + 0.587 * g + 0.114 * b)
        cb = int(-0.168736 * r - 0.331264 * g + 0.5 * b + 128)
        cr = int(0.5 * r - 0.418688 * g - 0.081312 * b + 128)
        return y, cb, cr

    def _find_best_rgb(self, r, g, b, target_cb_lsb, target_cr_lsb):
        min_dist = float("inf")
        best_rgb = (r, g, b)

        for dr in range(-3, 4):
            for dg in range(-3, 4):
                for db in range(-3, 4):
                    nr, ng, nb = r + dr, g + dg, b + db
                    if 0 <= nr <= 255 and 0 <= ng <= 255 and 0 <= nb <= 255:
                        _, cb, cr = self._rgb_to_ycbcr(nr, ng, nb)
                        if (cb & 1) == target_cb_lsb and (cr & 1) == target_cr_lsb:
                            dist = dr**2 + dg**2 + db**2
                            if dist < min_dist:
                                min_dist = dist
                                best_rgb = (nr, ng, nb)
                                if dist <= 1:
                                    return best_rgb
        return best_rgb

    def encode(self, image_path: str, payload: bytes, output_path: str):
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError("Image could not be read.")

        payload += self.DELIMITER
        binary_data = "".join(format(byte, "08b") for byte in payload)
        data_len = len(binary_data)

        rows, cols, channels = img.shape
        max_capacity = rows * cols * 2

        if data_len > max_capacity:
            raise ValueError(f"Payload too large. Max capacity: {max_capacity} bits.")

        bit_idx = 0
        for i in range(rows):
            for j in range(cols):
                if bit_idx >= data_len:
                    break

                b, g, r = int(img[i, j][0]), int(img[i, j][1]), int(img[i, j][2])

                target_cb_lsb = (
                    int(binary_data[bit_idx]) if bit_idx < data_len else (self._rgb_to_ycbcr(r, g, b)[1] & 1)
                )
                bit_idx += 1

                target_cr_lsb = (
                    int(binary_data[bit_idx]) if bit_idx < data_len else (self._rgb_to_ycbcr(r, g, b)[2] & 1)
                )
                bit_idx += 1

                new_r, new_g, new_b = self._find_best_rgb(r, g, b, target_cb_lsb, target_cr_lsb)
                img[i, j] = [new_b, new_g, new_r]

        cv2.imwrite(output_path, img)

    def decode(self, image_path: str) -> bytes:
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError("Image could not be read.")

        rows, cols, _ = img.shape
        extracted_bits = []

        for i in range(rows):
            for j in range(cols):
                b, g, r = img[i, j]
                _, cb, cr = self._rgb_to_ycbcr(r, g, b)
                extracted_bits.append(str(cb & 1))
                extracted_bits.append(str(cr & 1))

        bits_str = "".join(extracted_bits)
        bytes_array = bytearray()
        for i in range(0, len(bits_str), 8):
            byte = bits_str[i : i + 8]
            if len(byte) == 8:
                bytes_array.append(int(byte, 2))

            if i % 64 == 0 and self.DELIMITER in bytes_array:
                return bytes_array.split(self.DELIMITER)[0]

        return bytes_array
