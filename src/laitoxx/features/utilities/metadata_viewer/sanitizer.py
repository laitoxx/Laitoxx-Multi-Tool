import logging
import os

try:
    import pyexiv2

    HAS_EXIV2 = True
except ImportError:
    HAS_EXIV2 = False

try:
    import mutagen

    HAS_MUTAGEN = True
except ImportError:
    HAS_MUTAGEN = False


class MetadataSanitizer:
    @staticmethod
    def sanitize(filepath: str) -> bool:
        """
        Wipes metadata from the file using specialized libraries.
        Currently supports images (via pyexiv2) and media (via mutagen).
        Returns True if successful.
        """
        if not os.path.exists(filepath):
            return False

        ext = os.path.splitext(filepath)[1].lower()
        success = False

        # Images
        if HAS_EXIV2 and ext in [".jpg", ".jpeg", ".png", ".tiff", ".webp"]:
            try:
                with pyexiv2.Image(filepath) as img:
                    img.clear_exif()
                    img.clear_xmp()
                    img.clear_iptc()
                success = True
            except Exception as e:
                logging.error(f"pyexiv2 sanitize failed for {filepath}: {e}")

        # Audio / Video
        elif HAS_MUTAGEN and ext in [".mp3", ".flac", ".ogg", ".mp4", ".m4a"]:
            try:
                audio = mutagen.File(filepath)
                if audio is not None:
                    audio.delete()
                    audio.save()
                    success = True
            except Exception as e:
                logging.error(f"mutagen sanitize failed for {filepath}: {e}")

        else:
            logging.warning(f"No sanitizer available for format {ext}")

        return success
