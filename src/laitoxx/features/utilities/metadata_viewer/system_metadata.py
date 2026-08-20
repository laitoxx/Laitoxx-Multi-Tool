"""MIME, filesystem attribute, and hash extraction."""

import hashlib
import os
import platform

try:
    import magic
except ImportError:
    magic = None

try:
    import xattr
except ImportError:
    xattr = None

HAS_MAGIC = magic is not None
HAS_XATTR = xattr is not None


class SystemMetadataMixin:
    def get_mime_type(self, filepath: str) -> str:
        if HAS_MAGIC:
            try:
                # python-magic format
                return magic.from_file(filepath, mime=True)
            except Exception:
                pass
        import mimetypes

        return mimetypes.guess_type(filepath)[0] or "application/octet-stream"

    def _extract_os_attributes(self, filepath: str, data: dict):
        if platform.system() == "Windows":
            try:
                zone_file = filepath + ":Zone.Identifier"
                if os.path.exists(zone_file):
                    with open(zone_file) as f:
                        data["ADS:Zone.Identifier"] = f.read().strip()
                        data["ExtractedWith"].append("ADS")
            except Exception:
                pass
        else:
            if HAS_XATTR:
                try:
                    attrs = xattr.listxattr(filepath)
                    if attrs:
                        data["ExtractedWith"].append("xattr")
                        for attr in attrs:
                            val = xattr.getxattr(filepath, attr)
                            try:
                                data[f"xattr:{attr}"] = val.decode("utf-8")
                            except UnicodeDecodeError:
                                data[f"xattr:{attr}"] = f"<Binary Data: {len(val)} bytes>"
                except Exception:
                    pass

    def _compute_hash(self, filepath: str, algo: str) -> str:
        h = hashlib.new(algo)
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
            return h.hexdigest()
        except Exception:
            return ""
