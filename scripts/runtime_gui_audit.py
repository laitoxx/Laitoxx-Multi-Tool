"""Runtime constructor audit for project-owned Qt widgets.

This is a developer diagnostic, not a test suite.  It imports every package
module, discovers concrete QWidget subclasses and constructs them with small
local fixtures.  Network and QtWebEngine work is intentionally disabled.
"""

from __future__ import annotations

import importlib
import inspect
import os
import pkgutil
import sys
import traceback
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PyQt6.QtWidgets import QApplication, QWidget  # noqa: E402


def _fixture(parameter: inspect.Parameter, created: dict[str, QWidget]):
    name = parameter.name.lower()
    if name in {"parent", "host"}:
        return None
    if name in {
        "text",
        "title",
        "label",
        "name",
        "message",
        "tool_name",
        "mode",
        "prompt",
        "icon",
        "snippet_key",
    }:
        if name == "snippet_key":
            return "json_parse"
        return "demo"
    if "theme" in name:
        return {}
    if name in {"nodes", "edges", "items", "results", "checks", "commands", "entities", "fields"}:
        return []
    if name in {"data", "metadata", "info", "config", "settings", "payload", "plugin_data"}:
        return {}
    if name == "value":
        return "0"
    if name in {"minimum", "maximum", "index", "count"}:
        return 0
    if name in {"checked", "enabled", "editable"}:
        return False
    if name == "editor":
        editor = created.get("LuaCodeEditor")
        if editor is None:
            from laitoxx.interfaces.gui.plugin_code_editor import LuaCodeEditor

            editor = LuaCodeEditor()
            created["LuaCodeEditor"] = editor
        return editor
    if name == "result":
        from laitoxx.features.osint.username_osint.models import CheckResult

        return CheckResult("demo", "https://example.invalid/demo")
    raise LookupError(parameter.name)


def _arguments(cls: type[QWidget], created: dict[str, QWidget]) -> tuple[list, dict]:
    try:
        signature = inspect.signature(cls)
    except ValueError:
        # SIP subclasses which inherit a Qt constructor do not expose a Python
        # signature.  Text is accepted by both QPushButton and QLabel.
        return ["demo"], {}
    args: list[object] = []
    kwargs: dict[str, object] = {}
    for parameter in signature.parameters.values():
        if parameter.kind in (parameter.VAR_POSITIONAL, parameter.VAR_KEYWORD):
            continue
        if parameter.default is not parameter.empty:
            continue
        value = _fixture(parameter, created)
        if parameter.kind is parameter.POSITIONAL_ONLY:
            args.append(value)
        else:
            kwargs[parameter.name] = value
    return args, kwargs


def main() -> int:
    app = QApplication.instance() or QApplication([])
    import laitoxx

    modules = []
    import_errors = []
    for item in pkgutil.walk_packages(laitoxx.__path__, laitoxx.__name__ + "."):
        if item.name.endswith(("AppleWLoc_pb2", "BSSIDApple_pb2")):
            continue
        try:
            modules.append(importlib.import_module(item.name))
        except Exception:
            import_errors.append((item.name, traceback.format_exc()))

    # Chromium cannot start in the automation desktop session.  Exercise the
    # application's documented fallback instead of instantiating WebEngine.
    network_module = importlib.import_module("laitoxx.interfaces.gui.network_info_window")
    network_module.QWebEngineView = None
    network_module.QWebEngineSettings = None

    classes: set[type[QWidget]] = set()
    for module in modules:
        for value in vars(module).values():
            if (
                inspect.isclass(value)
                and value.__module__ == module.__name__
                and issubclass(value, QWidget)
                and value is not QWidget
            ):
                classes.add(value)

    created: dict[str, QWidget] = {}
    constructed = 0
    skipped = []
    failed = []
    for cls in sorted(classes, key=lambda value: (value.__module__, value.__name__)):
        try:
            args, kwargs = _arguments(cls, created)
        except (LookupError, ValueError) as exc:
            skipped.append((f"{cls.__module__}.{cls.__name__}", str(exc)))
            continue
        try:
            widget = cls(*args, **kwargs)
            created[cls.__name__] = widget
            constructed += 1
            app.processEvents()
        except Exception:
            failed.append((f"{cls.__module__}.{cls.__name__}", traceback.format_exc()))

    for widget in reversed(list(created.values())):
        widget.close()
        widget.deleteLater()
    app.processEvents()

    print(f"classes={len(classes)} constructed={constructed} skipped={len(skipped)} failed={len(failed)}")
    for name, reason in skipped:
        print(f"SKIP {name}: {reason}")
    for name, error in failed:
        print(f"FAIL {name}\n{error}")
    for name, error in import_errors:
        print(f"IMPORT_FAIL {name}\n{error}")
    return int(bool(failed or import_errors))


if __name__ == "__main__":
    raise SystemExit(main())
