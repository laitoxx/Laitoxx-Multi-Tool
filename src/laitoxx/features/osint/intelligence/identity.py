"""Avatar fingerprinting and explainable username/account correlation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps, ImageStat


def _bits_to_hex(bits) -> str:
    bits = list(bits)
    return f"{int(''.join('1' if bit else '0' for bit in bits), 2):0{len(bits) // 4}x}"


def _dhash(image: Image.Image, size: int = 8) -> str:
    gray = ImageOps.grayscale(image).resize((size + 1, size), Image.Resampling.LANCZOS)
    pixels = list(gray.getdata())
    return _bits_to_hex(
        pixels[row * (size + 1) + col] > pixels[row * (size + 1) + col + 1]
        for row in range(size)
        for col in range(size)
    )


def _ahash(image: Image.Image, size: int = 8) -> str:
    gray = ImageOps.grayscale(image).resize((size, size), Image.Resampling.LANCZOS)
    pixels = list(gray.getdata())
    mean = sum(pixels) / len(pixels)
    return _bits_to_hex(pixel >= mean for pixel in pixels)


def _distance(left: str, right: str) -> int:
    return (int(left, 16) ^ int(right, 16)).bit_count()


def avatar_fingerprint(path: str) -> dict[str, Any]:
    raw = Path(path).read_bytes()
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
        stat = ImageStat.Stat(image.resize((1, 1)))
        return {
            "file": str(path),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "width": image.width,
            "height": image.height,
            "aspect_ratio": round(image.width / image.height, 4),
            "dhash": _dhash(image),
            "ahash": _ahash(image),
            "mean_rgb": [round(value, 2) for value in stat.mean],
            "flipped_dhash": _dhash(ImageOps.mirror(image)),
            "center_crop_dhash": _dhash(ImageOps.fit(image, (256, 256))),
        }


def compare_avatars(first_path: str, second_path: str) -> dict[str, Any]:
    first = avatar_fingerprint(first_path)
    second = avatar_fingerprint(second_path)
    direct = _distance(first["dhash"], second["dhash"])
    flipped = _distance(first["dhash"], second["flipped_dhash"])
    cropped = _distance(first["center_crop_dhash"], second["center_crop_dhash"])
    best = min(direct, flipped, cropped)
    similarity = round((1 - best / 64) * 100, 1)
    variant = ["direct", "mirrored", "center-cropped"][[direct, flipped, cropped].index(best)]
    return {
        "similarity": similarity,
        "best_variant": variant,
        "hamming_distance": best,
        "exact_file": first["sha256"] == second["sha256"],
        "first": first,
        "second": second,
    }


@dataclass(frozen=True)
class AccountProfile:
    username: str
    platform: str = ""
    display_name: str = ""
    bio: str = ""
    avatar_hash: str = ""
    links: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, data: dict):
        return cls(
            username=str(data.get("username", "")),
            platform=str(data.get("platform", "")),
            display_name=str(data.get("display_name", "")),
            bio=str(data.get("bio", "")),
            avatar_hash=str(data.get("avatar_hash", "")),
            links=tuple(data.get("links", []) or []),
        )


def correlate_profiles(first: AccountProfile, second: AccountProfile) -> dict:
    score = 0.0
    reasons = []
    username_ratio = SequenceMatcher(None, first.username.casefold(), second.username.casefold()).ratio()
    score += username_ratio * 40
    reasons.append(f"username similarity: {username_ratio:.0%}")
    if first.display_name and second.display_name:
        ratio = SequenceMatcher(None, first.display_name.casefold(), second.display_name.casefold()).ratio()
        score += ratio * 20
        reasons.append(f"display name similarity: {ratio:.0%}")
    if first.avatar_hash and second.avatar_hash:
        distance = _distance(first.avatar_hash, second.avatar_hash)
        avatar_score = max(0, 1 - distance / 64)
        score += avatar_score * 25
        reasons.append(f"avatar similarity: {avatar_score:.0%}")
    shared_links = set(map(str.casefold, first.links)) & set(map(str.casefold, second.links))
    if shared_links:
        score += min(15, len(shared_links) * 7.5)
        reasons.append(f"shared links: {len(shared_links)}")
    elif first.bio and second.bio:
        bio_ratio = SequenceMatcher(None, first.bio.casefold(), second.bio.casefold()).ratio()
        score += bio_ratio * 10
        reasons.append(f"bio similarity: {bio_ratio:.0%}")
    return {"score": round(min(score, 100), 1), "reasons": reasons, "first": asdict(first), "second": asdict(second)}


def correlate_many(profiles: list[AccountProfile]) -> list[dict]:
    results = []
    for index, first in enumerate(profiles):
        for second in profiles[index + 1 :]:
            results.append(correlate_profiles(first, second))
    return sorted(results, key=lambda item: item["score"], reverse=True)


def avatar_fingerprint_tool(value: str | None = None):
    value = value if value is not None else input("path1 | path2: ")
    paths = [part.strip() for part in value.split("|", 1)]
    result = compare_avatars(*paths) if len(paths) == 2 else avatar_fingerprint(paths[0])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def username_correlation_tool(value: str | None = None):
    value = value if value is not None else input()
    try:
        raw = json.loads(value)
        profiles = [AccountProfile.from_mapping(item) for item in raw]
    except (json.JSONDecodeError, TypeError):
        profiles = [AccountProfile(username=item.strip()) for item in value.splitlines() if item.strip()]
    result = correlate_many(profiles)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result
