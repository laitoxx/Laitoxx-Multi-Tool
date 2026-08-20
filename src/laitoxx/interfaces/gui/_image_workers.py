"""
_image_workers.py - Background QObject workers for ImageSearchWindow.

Each worker is designed to run in a dedicated QThread:
  - SearchWorker   - uploads image, builds reverse-search URLs
  - HashWorker     - computes cryptographic and perceptual hashes
  - ForensicsWorker - runs EXIF / ELA / clone / noise / color analysis
"""

from __future__ import annotations

import base64
import hashlib
import io
from typing import Any

from PyQt6.QtCore import QObject, pyqtSignal

try:
    from PIL import Image

    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import imagehash as _imagehash

    HAS_IMAGEHASH = True
except ImportError:
    HAS_IMAGEHASH = False

try:
    import requests as _requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


def pil_to_qpixmap(pil_img: Image.Image):
    """Convert a PIL image into a QPixmap."""
    from PyQt6.QtGui import QPixmap

    buf = io.BytesIO()
    pil_img.convert("RGBA").save(buf, "PNG")
    buf.seek(0)
    px = QPixmap()
    px.loadFromData(buf.read())
    return px


# ---------------------------------------------------------------------------
# SearchWorker
# ---------------------------------------------------------------------------

_SEARCH_ENGINE_MAP: dict[str, str] = {
    "Yandex": "https://yandex.ru/images/search?rpt=imageview&url={enc}",
    "Google Lens": "https://lens.google.com/uploadbyurl?url={enc}",
    "Bing": "https://www.bing.com/images/search?view=detailv2&iss=sbi&q=imgurl:{enc}",
    "SauceNao": "https://saucenao.com/search.php?url={enc}",
    "IQDB": "https://iqdb.org/?url={enc}",
    "Ascii2D": "https://ascii2d.net/search/url/{enc}",
    "TraceMoe": "https://trace.moe/?url={enc}",
    "Baidu": "https://image.baidu.com/search/index?tn=baiduimage&word={enc}",
    "Sogou": "https://pic.sogou.com/ris?query={enc}",
    "TinEye": "https://tineye.com/search?url={enc}",
}


class SearchWorker(QObject):
    finished = pyqtSignal(dict)  # {engine: url}
    error = pyqtSignal(str)

    def __init__(self, pil_img: Image.Image, engines: list[str]) -> None:
        super().__init__()
        self._img = pil_img
        self._engines = engines

    def run(self) -> None:
        import traceback
        import urllib.parse

        try:
            buf = io.BytesIO()
            self._img.convert("RGB").save(buf, "JPEG", quality=90)
            b64 = base64.b64encode(buf.getvalue()).decode()

            upload_url = ""
            if HAS_REQUESTS:
                try:
                    resp = _requests.post(
                        "https://reverseimg.net/api/upload",
                        json={"imageBase64": b64},
                        headers={
                            "User-Agent": "Mozilla/5.0 LAITOXX/2.2",
                            "Content-Type": "application/json",
                        },
                        timeout=15,
                    )
                    upload_url = resp.json().get("url", "")
                except Exception as e:
                    self.error.emit(f"Ошибка загрузки: {e}")
                    return

            enc = urllib.parse.quote(upload_url, safe="")
            urls = {eng: tpl.format(enc=enc) for eng, tpl in _SEARCH_ENGINE_MAP.items() if eng in self._engines}
            self.finished.emit(urls)
        except Exception:
            self.error.emit(traceback.format_exc())


# ---------------------------------------------------------------------------
# HashWorker
# ---------------------------------------------------------------------------

_CRYPTO_HASHES: tuple[tuple[str, Any], ...] = (
    ("MD5", hashlib.md5),
    ("SHA-1", hashlib.sha1),
    ("SHA-256", hashlib.sha256),
    ("SHA-512", hashlib.sha512),
    ("BLAKE2b", hashlib.blake2b),
)

_PERCEPTUAL_HASHES: tuple[str, ...] = ("pHash", "aHash", "dHash", "wHash")


class HashWorker(QObject):
    finished = pyqtSignal(dict)

    def __init__(self, path: str, pil_img: Image.Image) -> None:
        super().__init__()
        self._path = path
        self._img = pil_img

    def run(self) -> None:
        result: dict[str, str] = {}

        try:
            with open(self._path, "rb") as fh:
                data = fh.read()
            for name, fn in _CRYPTO_HASHES:
                result[name] = fn(data).hexdigest()
        except Exception as e:
            result["error_crypto"] = str(e)

        if HAS_IMAGEHASH and self._img:
            try:
                result["pHash"] = str(_imagehash.phash(self._img))
                result["aHash"] = str(_imagehash.average_hash(self._img))
                result["dHash"] = str(_imagehash.dhash(self._img))
                result["wHash"] = str(_imagehash.whash(self._img))
            except Exception:
                for h in _PERCEPTUAL_HASHES:
                    result[h] = "требуется imagehash"
        else:
            for h in _PERCEPTUAL_HASHES:
                result[h] = "требуется imagehash"

        self.finished.emit(result)


# ---------------------------------------------------------------------------
# ForensicsWorker
# ---------------------------------------------------------------------------


from ._image_forensics import ImageForensicsMixin


class ForensicsWorker(ImageForensicsMixin, QObject):
    finished = pyqtSignal(dict)
    progress = pyqtSignal(int)

    def __init__(
        self,
        pil_img: Image.Image,
        path: str,
        checks: dict[str, bool],
    ) -> None:
        super().__init__()
        self._img = pil_img
        self._path = path
        self._checks = checks

    def run(self) -> None:
        report: dict[str, Any] = {}
        total = sum(1 for v in self._checks.values() if v)
        if total == 0:
            self.finished.emit(report)
            return

        step = 0

        def _advance() -> None:
            nonlocal step
            step += 1
            self.progress.emit(int(step / total * 100))

        _check_map = {
            "exif": self._analyze_exif,
            "ela": self._analyze_ela,
            "clone": self._analyze_clone,
            "noise": self._analyze_noise,
            "color": self._analyze_color,
        }

        for key, analyzer in _check_map.items():
            if self._checks.get(key) and HAS_PIL:
                try:
                    report[key] = analyzer()
                except Exception as e:
                    report[key] = {"error": str(e)}
                _advance()

        self.finished.emit(report)
