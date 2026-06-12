from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
MAX_DEPTH = 5
MAX_FILE_LINES = 300

FORBIDDEN_ROOT_DIRS = {"gui", "tui", "settings", "script", "bd", "translations"}
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
    "src/laitoxx/shared/graph/mermaid.py",
    "src/laitoxx/shared/graph/model.py",
    "src/laitoxx/interfaces/gui/plugin_builder.py",
    "src/laitoxx/interfaces/gui/graph_editor.py",
    "src/laitoxx/interfaces/gui/theme_editor.py",
    "src/laitoxx/interfaces/gui/main_window.py",
    "src/laitoxx/interfaces/gui/image_search_window.py",
    "src/laitoxx/interfaces/gui/worker.py",
    "src/laitoxx/interfaces/gui/username_osint_window.py",
    "src/laitoxx/interfaces/gui/_image_workers.py",
    "src/laitoxx/interfaces/gui/dialogs.py",
    "src/laitoxx/features/utilities/metadata_viewer/engine.py",
    "src/laitoxx/features/utilities/metadata_viewer/gui_window.py",
    "src/laitoxx/features/network/ip_info.py",
    "src/laitoxx/features/web_audit/web_security_tools.py",
    "src/laitoxx/features/osint/username_osint/checker.py",
    "src/laitoxx/features/osint/username_osint/_patterns.py",
    "src/laitoxx/features/osint/username_osint/nickname_generator.py",
    "src/laitoxx/features/osint/google_osint.py",
    "src/laitoxx/features/osint/data_search.py",
    "src/laitoxx/core/settings/settings_window.py",
    "src/laitoxx/core/settings/network_manager.py",
    "src/laitoxx/core/localization/i18n.py",
    "src/laitoxx/app/plugins/engine.py",
    "tests/test_graph_api.py",
    "src/laitoxx/features/utilities/text_transformer.py",
    "src/laitoxx/features/network/BSSIDApple_pb2.py",
    "src/laitoxx/features/crypto/jwt_analyzer.py",
    "src/laitoxx/interfaces/gui/network_info_window.py",
}

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
    paths.extend((ROOT / "tests").rglob("*.py"))
    paths.extend(
        path
        for path in (ROOT / "cli.py", ROOT / "gui.py", ROOT / "install.py")
        if path.exists()
    )
    paths.extend((ROOT / "laitoxx").rglob("*.py"))
    return [path for path in paths if "__pycache__" not in path.parts]


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def check_root_dirs() -> list[str]:
    errors = []
    for name in sorted(FORBIDDEN_ROOT_DIRS):
        if (ROOT / name).exists() and not (ROOT / name).is_file():
            # some like translations might be valid if they are properly moved, 
            # but let's just warn if they exist as a package
            if (ROOT / name / "__init__.py").exists():
                errors.append(f"legacy root directory still exists: {name}/")
    return errors


def check_file_size(path: Path) -> list[str]:
    relative = rel(path)
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").count("\n") + 1
    except OSError as exc:
        return [f"cannot read {relative}: {exc}"]
    if lines > MAX_FILE_LINES and relative not in LARGE_FILE_BASELINE:
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
