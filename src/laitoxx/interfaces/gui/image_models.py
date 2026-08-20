"""Configuration models for the image-search workspace."""

_ENGINE_GROUPS: list[tuple[str, list[str]]] = [
    ("is_group_general", ["Yandex", "Google Lens", "Bing"]),
    ("is_group_anime", ["SauceNao", "IQDB", "Ascii2D", "TraceMoe"]),
    ("is_group_asian", ["Baidu", "Sogou"]),
    ("is_group_other", ["TinEye"]),
]

_ENGINE_GROUP_FALLBACKS: dict[str, str] = {
    "is_group_general": "General",
    "is_group_anime": "Anime / Art",
    "is_group_asian": "Asian",
    "is_group_other": "Other",
}

_DEFAULT_ENGINES_ON = {"Yandex", "Google Lens", "SauceNao", "IQDB"}

_SLIDER_DEFS: list[tuple[str, str, int, int]] = [
    ("brightness", "is_slider_brightness", -100, 100),
    ("contrast", "is_slider_contrast", -100, 100),
    ("saturation", "is_slider_saturation", -100, 100),
    ("exposure", "is_slider_exposure", -100, 100),
    ("shadows", "is_slider_shadows", -100, 100),
    ("highlights", "is_slider_highlights", -100, 100),
    ("warmth", "is_slider_warmth", -100, 100),
    ("sharpness", "is_slider_sharpness", -100, 100),
    ("blur", "is_slider_blur", 0, 100),
    ("grain", "is_slider_grain", 0, 100),
    ("noise", "is_slider_noise", 0, 100),
    ("fade", "is_slider_fade", 0, 100),
]

_HASH_ORDER = [
    "MD5",
    "SHA-1",
    "SHA-256",
    "SHA-512",
    "BLAKE2b",
    "pHash",
    "aHash",
    "dHash",
    "wHash",
]

_FORENSICS_CHECKS: list[tuple[str, str]] = [
    ("exif", "is_check_exif"),
    ("ela", "is_check_ela"),
    ("clone", "is_check_clone"),
    ("noise", "is_check_noise"),
    ("color", "is_check_color"),
]

_FORENSICS_CHECK_FALLBACKS: dict[str, str] = {
    "is_check_exif": "EXIF / Metadata",
    "is_check_ela": "ELA (Error Level Analysis)",
    "is_check_clone": "Clone Detection",
    "is_check_noise": "Noise Analysis",
    "is_check_color": "Color & White Balance",
}


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------
