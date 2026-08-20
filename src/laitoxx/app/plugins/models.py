"""
Lua Plugin Engine for Laitoxx.

Uses `lupa` (LuaJIT/Lua runtime for Python) to execute Lua plugins
inside a sandboxed environment with a rich host API.
"""

import os

from .lua_values import _lua_str as _lua_str
from .lua_values import _lua_table_to_dict as _lua_table_to_dict
from .lua_values import _lua_table_to_python as _lua_table_to_python
from .lua_values import _python_to_lua as _python_to_lua


class LuaPluginMeta:
    """Parsed metadata from a Lua plugin file."""

    def __init__(self, filepath: str, meta: dict):
        self.filepath = filepath
        self.id = meta.get("id", os.path.splitext(os.path.basename(filepath))[0])
        self.name = meta.get("name", self.id)
        self.description = meta.get("description", "")
        self.author = meta.get("author", "Unknown")
        self.version = meta.get("version", "1.0")
        self.plugin_type = meta.get("type", "search")  # search / processor / formatter / passive_scanner
        self.config_schema = meta.get("config_schema")  # list of {key, label, type, default, ...}
        self.enabled = True
        self.config_values: dict = {}  # filled from saved settings
