import struct
import zlib

from PIL import Image, ImageDraw, ImageFont


def make_png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    chunk_len = struct.pack(">I", len(data))
    chunk_crc = struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
    return chunk_len + chunk_type + data + chunk_crc


def encode_pngchunk(image_path: str, output_path: str, text: str, keyword: str = "stEg"):
    with open(image_path, "rb") as f:
        image_data = f.read()

    iend_pos = image_data.rfind(b"IEND")
    if iend_pos == -1:
        raise ValueError("Invalid PNG: IEND chunk not found")

    iend_pos -= 4

    chunk_data = keyword.encode("latin-1") + b"\x00" + text.encode("latin-1")
    new_chunk = make_png_chunk(b"tEXt", chunk_data)

    encoded_data = image_data[:iend_pos] + new_chunk + image_data[iend_pos:]

    with open(output_path, "wb") as f:
        f.write(encoded_data)


def decode_pngchunk(image_path: str, target_keyword: str = "stEg") -> str:
    with open(image_path, "rb") as f:
        image_data = f.read()

    if image_data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Invalid PNG signature")

    pos = 8
    while pos < len(image_data):
        length = struct.unpack(">I", image_data[pos : pos + 4])[0]
        chunk_type = image_data[pos + 4 : pos + 8].decode("latin-1")
        chunk_data = image_data[pos + 8 : pos + 8 + length]

        if chunk_type == "tEXt":
            null_pos = chunk_data.find(b"\x00")
            keyword = chunk_data[:null_pos].decode("latin-1")
            text = chunk_data[null_pos + 1 :].decode("latin-1")
            if keyword == target_keyword:
                return text

        if chunk_type == "IEND":
            break

        pos += 12 + length

    return ""


def encode_textoverlay(image_path: str, output_path: str, text: str, opacity: int = 2):
    img = Image.open(image_path).convert("RGBA")

    txt_overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(txt_overlay)

    font = ImageFont.load_default()

    draw.text((10, 10), text, font=font, fill=(255, 255, 255, opacity))

    result = Image.alpha_composite(img, txt_overlay)
    result.save(output_path, "PNG")


def decode_textoverlay(image_path: str) -> str:
    try:
        import pytesseract
    except ImportError:
        return "pytesseract not installed. Cannot decode TEXTOVERLAY."

    img = Image.open(image_path).convert("RGBA")

    extracted_text = pytesseract.image_to_string(img)
    return extracted_text.strip()
