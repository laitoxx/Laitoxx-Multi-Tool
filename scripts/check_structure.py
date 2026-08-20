from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
MAX_DEPTH = 5
MAX_FILE_LINES = 300

FORBIDDEN_ROOT_DIRS = {"gui", "tui", "settings", "script", "translations"}
FORBIDDEN_IMPORT_ROOTS = {
    "gui",
    "tui",
    "settings",
    "script",
    "lua_engine",
    "plugin_builder",
    "i18n",
}

LARGE_FILE_BASELINE = {
    # Existing decomposition debt. New files over MAX_FILE_LINES still fail.
    "src/laitoxx/core/settings/settings_window_part1.py",
    "src/laitoxx/features/network/masscan_scanner/scanner.py",
    "src/laitoxx/features/osint/advanced_web_scanner/local_scanners.py",
    "src/laitoxx/features/osint/advanced_web_scanner/provider/leakix.py",
    "src/laitoxx/features/osint/advanced_web_scanner/provider/vulnerabilities.py",
    "src/laitoxx/features/osint/advanced_web_scanner/shodan_filters.py",
    "src/laitoxx/features/osint/tongue/scanner/gift_recursive.py",
    "src/laitoxx/features/osint/tongue/service.py",
    "src/laitoxx/features/utilities/cognipass.py",
    "src/laitoxx/features/web_audit/crawler/service.py",
    "src/laitoxx/interfaces/gui/dialog_text_cipher.py",
    "src/laitoxx/interfaces/gui/advanced_web_scanner_window_part2.py",
    "src/laitoxx/interfaces/gui/graph_native_style.py",
    "src/laitoxx/interfaces/gui/masscan_window.py",
    "src/laitoxx/interfaces/gui/network_info_window_part1.py",
    "src/laitoxx/interfaces/gui/tongue_window_part2.py",
    "src/laitoxx/interfaces/gui/tongue_window_part3.py",
    "src/laitoxx/interfaces/gui/theme_widget_context.py",
    "src/laitoxx/interfaces/gui/username_window_part4.py",
    "src/laitoxx/interfaces/gui/web_crawler_window.py",
}

# Generated sources are not hand-maintained architecture debt. Their size is
# controlled by the upstream schema/compiler and they must not be hand-split.
GENERATED_FILE_EXEMPTIONS = set()


def main() -> int:
    errors: list[str] = []
    errors.extend(check_root_dirs())
    for path in python_files():
        errors.extend(check_file_size(path))
        errors.extend(check_depth(path))
        errors.extend(check_imports(path))

    if errors:
        print("Architecture check failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Architecture check passed.")
    return 0


def python_files() -> list[Path]:
    paths = list(SRC.rglob("*.py"))
    paths.extend(path for path in (ROOT / "cli.py", ROOT / "gui.py", ROOT / "install.py") if path.exists())
    paths.extend((ROOT / "laitoxx").rglob("*.py"))
    return [path for path in paths if "__pycache__" not in path.parts]


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def check_root_dirs() -> list[str]:
    errors = []
    for name in sorted(FORBIDDEN_ROOT_DIRS):
        if (ROOT / name).exists() and not (ROOT / name).is_file():
            errors.append(f"legacy root directory still exists: {name}/")
    return errors


def check_file_size(path: Path) -> list[str]:
    relative = rel(path)
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").count("\n") + 1
    except OSError as exc:
        return [f"cannot read {relative}: {exc}"]
    if lines > MAX_FILE_LINES and relative not in LARGE_FILE_BASELINE and relative not in GENERATED_FILE_EXEMPTIONS:
        return [f"{relative} has {lines} lines; split it or add an audited baseline entry"]
    return []


def check_depth(path: Path) -> list[str]:
    if not path.is_relative_to(SRC):
        return []
    depth = len(path.relative_to(SRC).parts) - 1
    if depth > MAX_DEPTH:
        return [f"{rel(path)} is nested {depth} levels under src; max is {MAX_DEPTH}"]
    return []


def check_imports(path: Path) -> list[str]:
    relative = rel(path)
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"), filename=relative)
    except SyntaxError as exc:
        return [f"{relative} has syntax error: {exc}"]

    errors = []
    for node in ast.walk(tree):
        imported = imported_module(node)
        if not imported:
            continue
        root = imported.split(".", 1)[0]
        if root in FORBIDDEN_IMPORT_ROOTS:
            errors.append(f"{relative} imports legacy module {imported}")
        if is_cross_feature_import(path, imported):
            errors.append(f"{relative} imports sibling feature {imported}")
    return errors


def imported_module(node: ast.AST) -> str | None:
    if isinstance(node, ast.Import):
        return node.names[0].name if node.names else None
    if isinstance(node, ast.ImportFrom):
        return node.module
    return None


def is_cross_feature_import(path: Path, imported: str) -> bool:
    prefix = "laitoxx.features."
    if not imported.startswith(prefix):
        return False
    try:
        relative = path.relative_to(SRC / "laitoxx" / "features")
    except ValueError:
        return False
    current_feature = relative.parts[0]
    imported_feature = imported.removeprefix(prefix).split(".", 1)[0]
    if imported_feature == "utilities":
        return False
    return imported_feature != current_feature


if __name__ == "__main__":
    raise SystemExit(main())
