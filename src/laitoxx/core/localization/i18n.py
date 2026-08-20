"""Single localization service backed exclusively by JSON catalogs."""

from __future__ import annotations

import json
from pathlib import Path

SUPPORTED_LANGUAGES = ("en", "ru", "uk", "tr")
TRANSLATIONS_DIR = Path(__file__).resolve().parent.parent / "translations"


def _load_catalog(language: str) -> dict[str, str]:
    path = TRANSLATIONS_DIR / f"{language}.json"
    try:
        with path.open(encoding="utf-8") as stream:
            data = json.load(stream)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


TRANSLATIONS: dict[str, dict[str, str]] = {language: _load_catalog(language) for language in SUPPORTED_LANGUAGES}


class Translator:
    def __init__(self, language: str = "en"):
        self.lang = language if language in TRANSLATIONS else "en"

    @property
    def language(self) -> str:
        return self.lang

    @language.setter
    def language(self, value: str) -> None:
        self.set_language(value)

    @property
    def translations(self) -> dict[str, dict[str, str]]:
        return TRANSLATIONS

    def set_language(self, language: str) -> None:
        if language in TRANSLATIONS:
            self.lang = language

    def get(self, key: str, **kwargs) -> str:
        value = TRANSLATIONS.get(self.lang, {}).get(key)
        if value is None:
            value = TRANSLATIONS.get("en", {}).get(key, key)
        return value.format(**kwargs) if isinstance(value, str) else str(value)


translator = Translator()
