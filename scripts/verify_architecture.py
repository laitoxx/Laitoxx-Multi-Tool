"""Verify feature boundaries, catalog integrity and source text policy."""

from __future__ import annotations

import ast
import json
import re
import sys
import tokenize
import unicodedata
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

_CYRILLIC_PATTERN = re.compile(r"[\u0400-\u04ff]")
_TEXT_SUFFIXES = {
    ".py",
    ".md",
    ".json",
    ".toml",
    ".yaml",
    ".yml",
    ".txt",
    ".lua",
    ".html",
    ".css",
    ".js",
    ".bat",
    ".sh",
    ".spec",
}
_IGNORED_PARTS = {".git", "venv", "cache", "logs", "runtime", "__pycache__", ".ruff_cache"}
_FORBIDDEN_ARTIFACTS = (
    "acquire_vis_network.py",
    "audiblecom.json",
    "debug_map.py",
    "hotel.json",
    "hyattscan.json",
    "lua_plugin_settings.json",
    "resources/avatar_cache",
    "settings",
    "src/settings",
    "src/laitoxx/core/settings/proxy.py",
    "src/laitoxx/features/osint/tongue/cli.py",
    "src/laitoxx/features/utilities/text_transformer_engine",
    "src/laitoxx/features/utilities/text_transformer.py",
    "src/laitoxx/features/utilities/text_transformer_tables.py",
    "src/laitoxx/features/web_audit/web_crawler.py",
    "src/laitoxx/interfaces/gui/translator.py",
    "src/laitoxx/resources",
    "scripts/runtime_text_transformer_audit.py",
    "tools",
    "tripcomscan.json",
    "User Agreement.txt",
    "user_agreement_accepted.txt",
)


def _failures_for_legacy_artifacts() -> list[str]:
    return [
        f"Legacy or generated repository artifact exists: {relative}"
        for relative in _FORBIDDEN_ARTIFACTS
        if (ROOT / relative).exists()
    ]


def _failures_for_source_policy() -> list[str]:
    failures: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.casefold() not in _TEXT_SUFFIXES:
            continue
        if any(part in _IGNORED_PARTS or part.startswith(".pytest") for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if any(
            ord(character) > 127 and (unicodedata.category(character) == "Pd" or character == "\u2212")
            for character in text
        ):
            failures.append(f"Typographic dash in {path.relative_to(ROOT)}")
    for path in [*SRC.rglob("*.py"), *(ROOT / "scripts").rglob("*.py")]:
        raw = path.read_bytes()
        try:
            for token in tokenize.tokenize(BytesIO(raw).readline):
                if token.type == tokenize.COMMENT and _CYRILLIC_PATTERN.search(token.string):
                    failures.append(f"Non-English comment in {path.relative_to(ROOT)}:{token.start[0]}")
            tree = ast.parse(raw.decode("utf-8"))
        except (SyntaxError, UnicodeDecodeError, tokenize.TokenError) as error:
            failures.append(f"Cannot parse {path.relative_to(ROOT)}: {error}")
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                docstring = ast.get_docstring(node, clean=False) or ""
                if _CYRILLIC_PATTERN.search(docstring):
                    failures.append(f"Non-English docstring in {path.relative_to(ROOT)}:{getattr(node, 'lineno', 1)}")
    return failures


def _failures_for_feature_boundaries() -> list[str]:
    failures: list[str] = []
    targets = [
        SRC / "laitoxx" / "features" / "web_audit" / "crawler",
        SRC / "laitoxx" / "features" / "web_audit" / "subdomain_discovery.py",
        SRC / "laitoxx" / "features" / "osint" / "username_osint",
    ]
    for target in targets:
        paths = [target] if target.is_file() else list(target.rglob("*.py"))
        for path in paths:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                names: list[str] = []
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module]
                for name in names:
                    if name.startswith("laitoxx.interfaces"):
                        failures.append(f"Feature imports GUI in {path.relative_to(ROOT)}: {name}")
    return failures


def _failures_for_catalog() -> list[str]:
    from laitoxx.app.tool_registry import CATEGORIES, TOOL_REGISTRY

    failures: list[str] = []
    if "Subdomain finder" in TOOL_REGISTRY:
        failures.append("Standalone Subdomain finder remains in the registry")
    if "Web Crawler" not in TOOL_REGISTRY:
        failures.append("Web Crawler is missing from the registry")
    listed = [name for tools in CATEGORIES.values() for name in tools]
    for name in listed:
        if name not in TOOL_REGISTRY:
            failures.append(f"Category references an unknown tool: {name}")
    for name, spec in TOOL_REGISTRY.items():
        try:
            if not callable(spec.func):
                failures.append(f"Tool handler is not callable: {name}")
        except Exception as error:
            failures.append(f"Tool handler failed to resolve: {name}: {error}")
    return failures


def main() -> int:
    failures = [
        *_failures_for_legacy_artifacts(),
        *_failures_for_source_policy(),
        *_failures_for_feature_boundaries(),
        *_failures_for_catalog(),
    ]
    for path in (SRC / "laitoxx" / "core" / "translations").glob("*.json"):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            failures.append(f"Invalid translation catalog {path.name}: {error}")
    if failures:
        print("Architecture verification failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("Architecture verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
