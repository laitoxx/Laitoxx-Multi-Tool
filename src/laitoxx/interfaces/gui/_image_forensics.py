"""Forensic analysis operations shared by image workers."""

from __future__ import annotations

import hashlib
import io
from typing import Any

try:
    from PIL import ExifTags, Image, ImageChops, ImageFilter, ImageStat
except ImportError:  # Optional image-forensics dependency.
    ExifTags = Image = ImageChops = ImageFilter = ImageStat = None


class ImageForensicsMixin:
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
