"""Date and CSS color representations."""

from __future__ import annotations

import colorsys
import math
from datetime import UTC, datetime
from email.utils import format_datetime, parsedate_to_datetime

from PIL import ImageColor


def _date(text: str) -> datetime:
    source = text.strip()
    try:
        parsed = datetime.fromisoformat(source.replace("Z", "+00:00"))
    except ValueError:
        parsed = parsedate_to_datetime(source)
    return parsed.replace(tzinfo=parsed.tzinfo or UTC).astimezone(UTC)


def date_format(mode: str, action: str, text: str, _options: dict) -> str:
    if mode == "unix_time":
        if action == "decode":
            return datetime.fromtimestamp(float(text), UTC).isoformat().replace("+00:00", "Z")
        return str(int(_date(text).timestamp()))
    value = _date(text)
    if mode == "w3c_date":
        return value.isoformat().replace("+00:00", "Z")
    if mode == "iso_date":
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")
    if mode == "iso_week":
        iso = value.isocalendar()
        return f"{iso.year}-W{iso.week:02d}-{iso.weekday}T{value:%H:%M:%SZ}"
    if mode == "iso_ordinal":
        return value.strftime("%Y-%jT%H:%M:%SZ")
    if mode == "rfc2822":
        return format_datetime(value, usegmt=True)
    if mode == "ctime":
        return value.ctime()
    if mode == "japanese_era":
        if value >= datetime(2019, 5, 1, tzinfo=UTC):
            year = value.year - 2018
            return f"令和{'元' if year == 1 else year}年{value.month}月{value.day}日"
        if value >= datetime(1989, 1, 8, tzinfo=UTC):
            return f"平成{value.year - 1988}年{value.month}月{value.day}日"
        if value >= datetime(1926, 12, 25, tzinfo=UTC):
            return f"昭和{value.year - 1925}年{value.month}月{value.day}日"
        return value.strftime("%Y-%m-%d")
    raise ValueError(f"Unknown date format: {mode}")


def _rgb(text: str) -> tuple[int, int, int]:
    source = text.strip()
    try:
        value = ImageColor.getrgb(source)
        return tuple(value[:3])
    except ValueError:
        values = [float(item.strip().rstrip("%")) for item in source.removeprefix("rgb(").removesuffix(")").split(",")]
        if len(values) != 3:
            raise ValueError("Use a CSS color, #RRGGBB or R,G,B") from None
        return tuple(max(0, min(255, round(value))) for value in values)


def _linear(channel: float) -> float:
    channel /= 255
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def _lab(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    red, green, blue = map(_linear, rgb)
    x = (red * 0.4124564 + green * 0.3575761 + blue * 0.1804375) / 0.95047
    y = red * 0.2126729 + green * 0.7151522 + blue * 0.072175
    z = (red * 0.0193339 + green * 0.119192 + blue * 0.9503041) / 1.08883

    def function(value):
        return value ** (1 / 3) if value > 0.008856 else 7.787 * value + 16 / 116

    fx, fy, fz = function(x), function(y), function(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def _oklab(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    red, green, blue = map(_linear, rgb)
    long_value = 0.4122214708 * red + 0.5363325363 * green + 0.0514459929 * blue
    medium_value = 0.2119034982 * red + 0.6806995451 * green + 0.1073969566 * blue
    short_value = 0.0883024619 * red + 0.2817188376 * green + 0.6299787005 * blue
    long_value, medium_value, short_value = long_value ** (1 / 3), medium_value ** (1 / 3), short_value ** (1 / 3)
    return (
        0.2104542553 * long_value + 0.793617785 * medium_value - 0.0040720468 * short_value,
        1.9779984951 * long_value - 2.428592205 * medium_value + 0.4505937099 * short_value,
        0.0259040371 * long_value + 0.7827717662 * medium_value - 0.808675766 * short_value,
    )


def color(mode: str, _action: str, text: str, _options: dict) -> str:
    rgb = _rgb(text)
    red, green, blue = rgb
    normalized = tuple(value / 255 for value in rgb)
    if mode == "color_name":
        known = {name: ImageColor.getrgb(value) for name, value in ImageColor.colormap.items()}
        return next((name for name, value in known.items() if value[:3] == rgb), "(no exact CSS color name)")
    if mode == "rgb_hex":
        return f"#{red:02X}{green:02X}{blue:02X}"
    if mode == "rgb":
        return f"rgb({red}, {green}, {blue})"
    hue, lightness, saturation = colorsys.rgb_to_hls(*normalized)
    if mode == "hsl":
        return f"hsl({hue * 360:.2f}, {saturation * 100:.2f}%, {lightness * 100:.2f}%)"
    if mode == "hwb":
        whiteness, blackness = min(normalized), 1 - max(normalized)
        return f"hwb({hue * 360:.2f} {whiteness * 100:.2f}% {blackness * 100:.2f}%)"
    if mode == "cmyk":
        key = 1 - max(normalized)
        cyan, magenta, yellow = ((1 - value - key) / (1 - key) if key < 1 else 0 for value in normalized)
        return f"cmyk({cyan * 100:.2f}%, {magenta * 100:.2f}%, {yellow * 100:.2f}%, {key * 100:.2f}%)"
    if mode in {"lab", "lch"}:
        light, a, b = _lab(rgb)
    else:
        light, a, b = _oklab(rgb)
    if mode in {"lch", "oklch"}:
        chroma, hue_angle = math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360
        return f"{mode}({light:.4f} {chroma:.4f} {hue_angle:.2f})"
    return f"{mode}({light:.4f} {a:.4f} {b:.4f})"
