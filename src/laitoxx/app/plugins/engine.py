"""
Lua Plugin Engine for Laitoxx.

Uses `lupa` (LuaJIT/Lua runtime for Python) to execute Lua plugins
inside a sandboxed environment with a rich host API.
"""

import json
import logging
import os
from collections.abc import Callable

try:
    from lupa import LuaError, LuaRuntime
except ImportError:
    LuaRuntime = None
    LuaError = Exception

from .discovery import (
    _load_plugin_meta as _load_plugin_meta,
)
from .discovery import (
    apply_settings_to_plugins as apply_settings_to_plugins,
)
from .discovery import (
    discover_lua_plugins as discover_lua_plugins,
)
from .discovery import (
    load_lua_plugin_settings as load_lua_plugin_settings,
)
from .discovery import (
    save_lua_plugin_settings as save_lua_plugin_settings,
)
from .host_api_graph import GraphHostMixin
from .host_api_services import ServiceHostMixin, apply_system_trust
from .host_api_username import UsernameHostMixin
from .lua_values import _lua_str as _lua_str
from .lua_values import _lua_table_to_dict as _lua_table_to_dict
from .lua_values import _lua_table_to_python as _lua_table_to_python
from .lua_values import _python_to_lua as _python_to_lua

# ---------------------------------------------------------------------------
# Host API  -  functions exposed to Lua scripts
# ---------------------------------------------------------------------------
from .models import LuaPluginMeta as LuaPluginMeta
from .sandbox import _create_sandbox_env as _create_sandbox_env


class HostAPI(GraphHostMixin, UsernameHostMixin, ServiceHostMixin):
    """
    The ``host`` table exposed inside Lua plugins.

    Every public method here becomes ``host.<method>()`` in Lua.
    """

    def __init__(
        self,
        plugin_meta: LuaPluginMeta,
        lua: "LuaRuntime",
        output_callback: Callable[[str], None] | None = None,
    ):
        self._meta = plugin_meta
        self._lua = lua
        self._raw_output = output_callback or (lambda msg: None)
        self._plugin_dir = os.path.dirname(plugin_meta.filepath)
        self._cache: dict = {}
        from laitoxx.core.settings.network_manager import get_session

        self._session = get_session()
        apply_system_trust(self._session)

    # -- Logging / output ---------------------------------------------------

    # -- HTTP ---------------------------------------------------------------

    # -- JSON ---------------------------------------------------------------

    # -- Files (sandboxed to plugin directory) ------------------------------

    # -- Config -------------------------------------------------------------

    # -- Utilities ----------------------------------------------------------

    # -- Cache (in-memory, per-session) -------------------------------------

    # -- Graph API ----------------------------------------------------------

    # -- Username OSINT API ------------------------------------------------


# ---------------------------------------------------------------------------
# Helpers  -  Lua <-> Python conversion
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Sandbox builder
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Plugin loader
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Plugin settings persistence
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Plugin executor
# ---------------------------------------------------------------------------


def run_lua_plugin(
    plugin: LuaPluginMeta,
    function_name: str,
    query: str = "",
    options: dict = None,
    output_callback: Callable[[str], None] = None,
    graph_callback: Callable[[str], None] = None,
) -> str | None:
    """
    Execute a function inside a Lua plugin.

    Parameters
    ----------
    plugin : LuaPluginMeta
    function_name : str
        The Lua function to call, e.g. ``"search"``, ``"process"``, ``"format"``.
    query : str
        The user-supplied input (search query, text, etc.).
    options : dict
        Additional options passed as a Lua table.
    output_callback : callable
        Called with each line of output (for real-time UI updates).
    graph_callback : callable
        Called with graph file path when plugin saves a graph.

    Returns
    -------
    str or None
        The text result returned by the plugin, or None on error.
    """
    if LuaRuntime is None:
        if output_callback:
            output_callback("Error: lupa is not installed. Run: pip install lupa")
        return None

    lua = LuaRuntime(unpack_returned_tuples=True)
    host = HostAPI(plugin, lua, output_callback)
    env = _create_sandbox_env(lua, host)

    try:
        with open(plugin.filepath, encoding="utf-8") as f:
            source = f.read()

        # Load and execute the plugin source inside the sandbox
        _lua_chunk = f"""
        function(source, env)
            local fn, err = load(source, "{plugin.id}", "t", env)
            if not fn then error(err) end
            return fn()
        end
        """
        loader = lua.eval(_lua_chunk)

        plugin_table = loader(source, env)

        if plugin_table is None or not hasattr(plugin_table, "__getitem__"):
            if output_callback:
                output_callback("Error: Plugin did not return a valid table.")
            return None

        # Get the requested function
        func = plugin_table[function_name]
        if func is None:
            if output_callback:
                output_callback(f"Error: Plugin does not define function '{function_name}'.")
            return None

        # Build options table
        opts = _python_to_lua(lua, options or {})

        # Call the plugin function
        result = func(str(query), opts)

        # Notify about saved graphs
        if graph_callback and hasattr(host, "_saved_graph_paths"):
            for gpath in host._saved_graph_paths:
                graph_callback(gpath)

        # Handle nil, error return pattern
        if result is None:
            return None

        # If result is a Lua table, convert and JSON-encode for display
        if hasattr(result, "items"):
            converted = _lua_table_to_python(result)
            return json.dumps(converted, indent=2, ensure_ascii=False)

        return str(result)

    except LuaError as e:
        msg = f"Lua Error in plugin '{plugin.name}': {e}"
        logging.error(msg)
        if output_callback:
            output_callback(msg)
        return None
    except Exception as e:
        msg = f"Error running plugin '{plugin.name}': {e}"
        logging.error(msg, exc_info=True)
        if output_callback:
            output_callback(msg)
        return None
