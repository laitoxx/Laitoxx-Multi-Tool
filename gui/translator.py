from __future__ import annotations

import json
import os

from i18n import TRANSLATIONS as LEGACY_TRANSLATIONS


def _load_json_translations() -> dict:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    out: dict[str, dict] = {}
    for lang in ("en", "ru"):
        path = os.path.join(base_dir, "translations", f"{lang}.json")
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                out[lang] = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
    return out


class Translator:
    def __init__(self):
        self.lang = 'en'
        merged = {}
        json_translations = _load_json_translations()
        for lang in set(LEGACY_TRANSLATIONS.keys()) | set(json_translations.keys()):
            merged[lang] = dict(json_translations.get(lang, {}))
            merged[lang].update(LEGACY_TRANSLATIONS.get(lang, {}))
        self.translations = merged

    def set_language(self, lang):
        if lang in self.translations:
            self.lang = lang

    def get(self, key, **kwargs):
        translation = self.translations.get(self.lang, {}).get(key, key)
        if isinstance(translation, str):
            return translation.format(**kwargs)
        return translation


translator = Translator()
