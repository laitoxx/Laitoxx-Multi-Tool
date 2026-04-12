"""
_image_workers.py — Background QObject workers for ImageSearchWindow.

Each worker is designed to run in a dedicated QThread:
  - SearchWorker   — uploads image, builds reverse-search URLs
  - HashWorker     — computes cryptographic and perceptual hashes
  - ForensicsWorker — runs EXIF / ELA / clone / noise / color analysis
"""
from __future__ import annotations

import base64
import hashlib
import io
import random
from typing import Any

from PyQt6.QtCore import QObject, pyqtSignal

try:
    from PIL import Image, ImageChops, ImageFilter, ImageStat, ExifTags
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


def pil_to_qpixmap(pil_img: "Image.Image"):
    """Конвертирует PIL Image в QPixmap."""
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
    "Yandex":      "https://yandex.ru/images/search?rpt=imageview&url={enc}",
    "Google Lens": "https://lens.google.com/uploadbyurl?url={enc}",
    "Bing":        "https://www.bing.com/images/search?view=detailv2&iss=sbi&q=imgurl:{enc}",
    "SauceNao":    "https://saucenao.com/search.php?url={enc}",
    "IQDB":        "https://iqdb.org/?url={enc}",
    "Ascii2D":     "https://ascii2d.net/search/url/{enc}",
    "TraceMoe":    "https://trace.moe/?url={enc}",
    "Baidu":       "https://image.baidu.com/search/index?tn=baiduimage&word={enc}",
    "Sogou":       "https://pic.sogou.com/ris?query={enc}",
    "TinEye":      "https://tineye.com/search?url={enc}",
}


class SearchWorker(QObject):
    finished = pyqtSignal(dict)   # {engine: url}
    error    = pyqtSignal(str)

    def __init__(self, pil_img: "Image.Image", engines: list[str]) -> None:
        super().__init__()
        self._img = pil_img
        self._engines = engines

    def run(self) -> None:
        import urllib.parse
        import traceback

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
            urls = {
                eng: tpl.format(enc=enc)
                for eng, tpl in _SEARCH_ENGINE_MAP.items()
                if eng in self._engines
            }
            self.finished.emit(urls)
        except Exception:
            self.error.emit(traceback.format_exc())


# ---------------------------------------------------------------------------
# HashWorker
# ---------------------------------------------------------------------------

_CRYPTO_HASHES: tuple[tuple[str, Any], ...] = (
    ("MD5",    hashlib.md5),
    ("SHA-1",  hashlib.sha1),
    ("SHA-256", hashlib.sha256),
    ("SHA-512", hashlib.sha512),
    ("BLAKE2b", hashlib.blake2b),
)

_PERCEPTUAL_HASHES: tuple[str, ...] = ("pHash", "aHash", "dHash", "wHash")


class HashWorker(QObject):
    finished = pyqtSignal(dict)

    def __init__(self, path: str, pil_img: "Image.Image") -> None:
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

class ForensicsWorker(QObject):
    finished = pyqtSignal(dict)
    progress = pyqtSignal(int)

    def __init__(
        self,
        pil_img: "Image.Image",
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
            "exif":  self._analyze_exif,
            "ela":   self._analyze_ela,
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

    def _analyze_exif(self) -> dict[str, Any]:
        img = self._img
        flags: list[str] = []
        raw: dict[str, str] = {}

        try:
            exif2 = img.getexif() or {}
            for k, v in exif2.items():
                name = ExifTags.TAGS.get(k, str(k))
                raw[name] = str(v)[:200]
        except Exception:
            pass

        try:
            exif_data = img._getexif() or {}
            for k, v in exif_data.items():
                name = ExifTags.TAGS.get(k, str(k))
                if name not in raw:
                    raw[name] = str(v)[:200]
        except Exception:
            pass

        sw = raw.get("Software", "")
        for editor in ("Photoshop", "GIMP", "Lightroom", "Affinity"):
            if editor.lower() in sw.lower():
                flags.append(f"Обнаружен редактор: {sw}")
                break

        if "DateTime" in raw and "DateTimeOriginal" in raw:
            if raw["DateTime"] != raw["DateTimeOriginal"]:
                flags.append("Дата изменения отличается от даты съёмки")

        return {"flags": flags, "raw": raw}

    def _analyze_ela(self) -> dict[str, Any]:
        img = self._img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=95)
        buf.seek(0)
        recomp = Image.open(buf).convert("RGB")
        diff = ImageChops.difference(img, recomp)
        ela = diff.point(lambda x: min(255, x * 10))
        stat = ImageStat.Stat(ela)
        mean_ela = sum(stat.mean) / 3
        verdict = "подозрительно" if mean_ela > 12 else "норма"
        return {"ela_image": ela, "mean": round(mean_ela, 2), "verdict": verdict}

    def _analyze_clone(self) -> dict[str, Any]:
        img = self._img.convert("L")
        w, h = img.size
        scale = min(1.0, 512 / max(w, h))
        nw, nh = int(w * scale), int(h * scale)
        img = img.resize((nw, nh), Image.LANCZOS)
        bw, bh = 16, 16
        hashes: dict[str, list] = {}
        for y in range(0, nh - bh, bh):
            for x in range(0, nw - bw, bw):
                box = img.crop((x, y, x + bw, y + bh))
                if ImageStat.Stat(box).stddev[0] < 2:
                    continue
                h_val = hashlib.md5(box.tobytes()).hexdigest()
                hashes.setdefault(h_val, []).append((x, y))
        dupes = {k: v for k, v in hashes.items() if len(v) > 1}
        return {"duplicate_blocks": len(dupes), "suspicious": len(dupes) > 5}

    def _analyze_noise(self) -> dict[str, Any]:
        img = self._img.convert("L")
        blurred = img.filter(ImageFilter.GaussianBlur(radius=2))
        diff = ImageChops.difference(img, blurred)
        w, h = diff.size
        bw, bh = w // 4, h // 4
        stds = []
        for row in range(4):
            for col in range(4):
                box = diff.crop((col * bw, row * bh, (col + 1) * bw, (row + 1) * bh))
                stds.append(ImageStat.Stat(box).stddev[0])
        stds = [s for s in stds if s > 0]
        if not stds:
            return {"suspicious": False, "note": "нет данных"}
        ratio = max(stds) / (min(stds) + 1e-9)
        return {
            "max_std": round(max(stds), 2),
            "min_std": round(min(stds), 2),
            "ratio": round(ratio, 2),
            "suspicious": ratio > 2.5,
        }

    def _analyze_color(self) -> dict[str, Any]:
        stat = ImageStat.Stat(self._img.convert("RGB"))
        r, g, b = stat.mean[:3]
        ratio_br = b / (r + 1e-9)
        warm = (r / (b + 1e-9)) > 1.15
        cool = ratio_br > 1.15
        wb = "тёплый" if warm else ("холодный" if cool else "нейтральный")
        return {
            "r_mean": round(r, 1),
            "g_mean": round(g, 1),
            "b_mean": round(b, 1),
            "white_balance": wb,
        }
