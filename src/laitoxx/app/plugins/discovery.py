"""
Lua Plugin Engine for Laitoxx.

Uses `lupa` (LuaJIT/Lua runtime for Python) to execute Lua plugins
inside a sandboxed environment with a rich host API.
"""

import json
import logging
import os
from pathlib import Path

from laitoxx.core.settings.paths import LUA_PLUGIN_SETTINGS_FILE, PROJECT_ROOT

try:
    from lupa import LuaError, LuaRuntime
except ImportError:
    LuaRuntime = None
    LuaError = Exception

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LUA_PLUGIN_DIR = PROJECT_ROOT / "lua_plugins"

# ---------------------------------------------------------------------------
# Lua Plugin metadata container
# ---------------------------------------------------------------------------


from .lua_values import _lua_str as _lua_str
from .lua_values import _lua_table_to_dict as _lua_table_to_dict
from .lua_values import _lua_table_to_python as _lua_table_to_python
from .lua_values import _python_to_lua as _python_to_lua
from .models import LuaPluginMeta


def _load_plugin_meta(filepath: str) -> LuaPluginMeta | None:
    """
    Read only the ``plugin`` metadata table from a Lua file
    without executing arbitrary code.

    The plugin file must define  ``local plugin = { ... }``  or
    ``plugin = { ... }``  and eventually ``return plugin``.
    We extract the table by running the script in a minimal sandbox.
    """
    if LuaRuntime is None:
        return None

    try:
        lua = LuaRuntime(unpack_returned_tuples=True)
        with open(filepath, encoding="utf-8") as f:
            source = f.read()

        # Run in a restricted env that only allows table construction
        extract = lua.eval("""
        function(source)
            local env = {
                type = type, tostring = tostring, tonumber = tonumber,
                pairs = pairs, ipairs = ipairs, next = next,
                string = string, table = table, math = math,
                setmetatable = setmetatable, getmetatable = getmetatable,
                error = error, pcall = pcall, select = select,
                unpack = unpack or table.unpack,
            }
            env._G = env
            local fn, err = load(source, "plugin_meta", "t", env)
            if not fn then return nil, err end
            local ok, result = pcall(fn)
            if not ok then return nil, result end
            if type(result) ~= "table" then return nil, "plugin must return a table" end
            return result
        end
        """)
        result = extract(source)

        if result is None:
            return None

        meta = _lua_table_to_python(result)
        if not isinstance(meta, dict):
            return None

        return LuaPluginMeta(filepath, meta)
    except Exception as e:
        logging.error(f"Failed to load Lua plugin meta from {filepath}: {e}")
        return None


def discover_lua_plugins(base_dir: str | Path = LUA_PLUGIN_DIR) -> list[LuaPluginMeta]:
    """Scan the lua_plugins directory and return metadata for each plugin."""
    plugins = []
    if not os.path.isdir(base_dir):
        return plugins
    for name in sorted(os.listdir(base_dir)):
        if not name.endswith(".lua") or name.startswith("_"):
            continue
        filepath = os.path.join(base_dir, name)
        meta = _load_plugin_meta(filepath)
        if meta:
            plugins.append(meta)
    return plugins


def load_lua_plugin_settings() -> dict:
    """Load saved plugin enable/disable state and config values."""
    if LUA_PLUGIN_SETTINGS_FILE.exists():
        try:
            with LUA_PLUGIN_SETTINGS_FILE.open(encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_lua_plugin_settings(settings: dict):
    LUA_PLUGIN_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LUA_PLUGIN_SETTINGS_FILE.open("w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)


def apply_settings_to_plugins(plugins: list[LuaPluginMeta], settings: dict):
    """Apply saved settings (enabled state, config values) to loaded plugins."""
    for p in plugins:
        ps = settings.get(p.id, {})
        p.enabled = ps.get("enabled", True)
        p.config_values = ps.get("config", {})
