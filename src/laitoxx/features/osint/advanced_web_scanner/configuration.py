from __future__ import annotations

import os
from copy import deepcopy

from laitoxx.core.localization.i18n import translator
from laitoxx.core.settings.app_settings import settings

from .catalog import BY_ID, PROVIDERS


def default_configuration() -> dict:
    return {
        "configured": False,
        "dns_mode": "doh",
        "enrichments": {
            "dns_consensus": True,
            "dns_security_posture": True,
            "dns_misconfiguration": True,
            "scope_classifier": True,
            "evidence_freshness": True,
            "routing_rpki": True,
            "technology_identity": True,
            "http_tls_posture": True,
            "archive_analysis": True,
        },
        "providers": {
            spec.id: {
                "enabled": True,
                "auth_mode": "key" if spec.key_required else "auto",
                "key": "",
            }
            for spec in PROVIDERS
        },
    }


def load_configuration() -> dict:
    base = default_configuration()
    saved = settings.advanced_web_scanner
    base["configured"] = bool(saved.get("configured", False))
    base["dns_mode"] = saved.get("dns_mode", "doh")
    if isinstance(saved.get("enrichments"), dict):
        base["enrichments"].update(saved["enrichments"])
    for provider_id, values in saved.get("providers", {}).items():
        if provider_id in base["providers"] and isinstance(values, dict):
            base["providers"][provider_id].update(values)
    # The minimum chain is a product invariant, not a user preference.
    for spec in PROVIDERS:
        if spec.mandatory:
            base["providers"][spec.id]["enabled"] = True
    return base


def save_configuration(config: dict) -> None:
    settings.advanced_web_scanner = deepcopy(config)


def provider_enabled(provider_id: str, config: dict | None = None) -> bool:
    return bool((config or load_configuration())["providers"].get(provider_id, {}).get("enabled", False))


def credential(provider_id: str, config: dict | None = None) -> str:
    spec = BY_ID[provider_id]
    stored = (config or load_configuration())["providers"].get(provider_id, {}).get("key", "")
    return os.getenv(spec.key_name, "").strip() if spec.key_name and os.getenv(spec.key_name) else str(stored).strip()


def auth_mode(provider_id: str, config: dict | None = None) -> str:
    cfg = config or load_configuration()
    choice = cfg["providers"].get(provider_id, {}).get("auth_mode", "auto")
    if choice == "anonymous":
        return "anonymous"
    return "key" if credential(provider_id, cfg) else "anonymous"


def configuration_errors(config: dict | None = None, profile: str = "minimum") -> list[str]:
    cfg = config or load_configuration()
    errors = []
    if not cfg.get("configured", False):
        errors.append(translator.get("aws_setup_initial_error"))
    for spec in PROVIDERS:
        item = cfg["providers"].get(spec.id, {})
        if spec.mandatory and not item.get("enabled", True):
            errors.append(translator.get("aws_mandatory_disabled_error", provider=spec.name))
        active = spec.mandatory or (profile == "maximum" and item.get("enabled", False))
        if active and spec.key_required and not credential(spec.id, cfg):
            errors.append(translator.get("aws_key_required_error", provider=spec.name))
    return errors
