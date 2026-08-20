import os

from PIL import Image

from laitoxx.features.utilities.shared_utils import Color
from laitoxx.features.utilities.steganography.crypto import decrypt, encrypt
from laitoxx.features.utilities.steganography.decoder import decode
from laitoxx.features.utilities.steganography.encoder import encode
from laitoxx.features.utilities.steganography.models import StegConfig


def steganography_tool(data=None):
    if data:
        # GUI mode
        mode = data.get("mode")
        image_path = data.get("image_path")
        password = data.get("password")
        message = data.get("message")
    else:
        # CLI mode
        print(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Steganography\n")
        mode = (
            input(f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Action (hide/extract): ")
            .strip()
            .lower()
        )
        image_path = input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Cover image path: "
        ).strip()
        if mode == "hide":
            message = input(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Secret text to hide: "
            ).strip()
        else:
            message = None
        password = input(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Password (optional): "
        ).strip()

    print(f"\n{Color.DARK_RED}┌─[ {Color.LIGHT_RED}Steganography Processing {Color.DARK_RED}]" + "─" * 20)

    if not os.path.exists(image_path):
        print(f"{Color.DARK_RED}Error: Image file not found.")
        print(f"{Color.DARK_RED}└" + "─" * 40)
        return

    try:
        if mode == "hide":
            print(f"{Color.WHITE}Opening cover image...")
            img = Image.open(image_path)

            raw_data = message.encode("utf-8")
            if password:
                print(f"{Color.WHITE}Encrypting data with password...")
                raw_data = encrypt(raw_data, password)

            config = StegConfig()

            print(f"{Color.WHITE}Embedding data using LSB...")
            result_img = encode(img, raw_data, config)

            out_path = os.path.splitext(image_path)[0] + "_steg.png"
            result_img.save(out_path, format="PNG")
            print(f"{Color.GREEN}Success! Saved to: {out_path}")

        elif mode == "extract":
            print(f"{Color.WHITE}Opening image for extraction...")
            img = Image.open(image_path)

            print(f"{Color.WHITE}Extracting hidden data...")
            raw_data = decode(img, verify_checksum=True)

            if password:
                print(f"{Color.WHITE}Decrypting data...")
                raw_data = decrypt(raw_data, password)

            text = raw_data.decode("utf-8")
            print(f"\n{Color.LIGHT_GREEN}--- HIDDEN MESSAGE ---")
            print(f"{Color.WHITE}{text}")
            print(f"{Color.LIGHT_GREEN}----------------------")

        else:
            print(f"{Color.DARK_RED}Unknown mode: {mode}")

    except Exception as e:
        print(f"{Color.DARK_RED}Error during {mode}: {e}")

    print(f"{Color.DARK_RED}└" + "─" * 40)
