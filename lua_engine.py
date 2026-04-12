"""
Lua Plugin Engine for Laitoxx.

Uses `lupa` (LuaJIT/Lua runtime for Python) to execute Lua plugins
inside a sandboxed environment with a rich host API.
"""

import os
import json
import time
import hashlib
import base64
import logging
import urllib.parse
import uuid
from typing import Optional, Callable

import requests

from gui.graph_model import Graph, Node, Edge, NODE_TYPE_DEFAULTS

try:
    from lupa import LuaRuntime, LuaError
except ImportError:
    LuaRuntime = None
    LuaError = Exception

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LUA_PLUGIN_DIR = "lua_plugins"
LUA_PLUGIN_CONFIG_FILE = "lua_plugin_settings.json"
TOOL_VERSION = "2.2.2"

# ---------------------------------------------------------------------------
# Lua Plugin metadata container
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Host API  –  functions exposed to Lua scripts
# ---------------------------------------------------------------------------

class HostAPI:
    """
    The ``host`` table exposed inside Lua plugins.

    Every public method here becomes ``host.<method>()`` in Lua.
    """

    def __init__(self, plugin_meta: LuaPluginMeta, lua: 'LuaRuntime',
                 output_callback: Optional[Callable[[str], None]] = None):
        self._meta = plugin_meta
        self._lua = lua
        self._raw_output = output_callback or (lambda msg: None)
        self._plugin_dir = os.path.dirname(plugin_meta.filepath)
        self._cache: dict = {}
        try:
            from settings.proxy import make_session
            from settings.app_settings import settings as _app_settings
            self._session = make_session(_app_settings.proxy)
        except Exception:
            self._session = requests.Session()

    def _output(self, msg):
        """Output with bytes-safe conversion."""
        if isinstance(msg, bytes):
            msg = msg.decode("utf-8", errors="replace")
        self._raw_output(str(msg))

    # -- Logging / output ---------------------------------------------------

    def log(self, message, level="info"):
        """Write a message to the application log and plugin output."""
        message = _lua_str(message)
        level = _lua_str(level).lower()
        log_fn = getattr(logging, level, logging.info)
        log_fn(f"[LuaPlugin:{self._meta.id}] {message}")
        self._output(f"[{level.upper()}] {message}")

    def print(self, *args):
        """Print to plugin output (shown in UI)."""
        text = " ".join(_lua_str(a) for a in args)
        self._output(text)

    # -- HTTP ---------------------------------------------------------------

    def http_get(self, url, timeout=15, headers_table=None):
        """Perform an HTTP GET request. Returns body string or nil+error."""
        try:
            headers = _lua_table_to_dict(headers_table) if headers_table else {}
            resp = self._session.get(str(url), timeout=int(timeout), headers=headers)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            return None, str(e)

    def http_post(self, url, data=None, timeout=15, headers_table=None, content_type="application/json"):
        """Perform an HTTP POST request. Returns body string or nil+error."""
        try:
            headers = _lua_table_to_dict(headers_table) if headers_table else {}
            headers.setdefault("Content-Type", str(content_type))
            body = data
            if hasattr(data, 'keys'):
                body = json.dumps(_lua_table_to_dict(data), ensure_ascii=False)
            if isinstance(body, str):
                body = body.encode('utf-8')
            resp = self._session.post(str(url), data=body, timeout=int(timeout), headers=headers)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            return None, str(e)

    # -- JSON ---------------------------------------------------------------

    def json_decode(self, text):
        """Parse a JSON string into a Lua table."""
        try:
            obj = json.loads(str(text))
            return _python_to_lua(self._lua, obj)
        except Exception as e:
            return None, str(e)

    def json_encode(self, lua_table):
        """Encode a Lua table into a JSON string."""
        try:
            obj = _lua_table_to_python(lua_table)
            return json.dumps(obj, ensure_ascii=False)
        except Exception as e:
            return None, str(e)

    # -- Files (sandboxed to plugin directory) ------------------------------

    def read_file(self, path):
        """Read a file relative to the plugin directory."""
        try:
            full = self._safe_path(str(path))
            with open(full, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return None, str(e)

    def write_file(self, path, content):
        """Write a file relative to the plugin directory."""
        try:
            full = self._safe_path(str(path))
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8") as f:
                f.write(str(content))
            return True
        except Exception as e:
            return None, str(e)

    def file_exists(self, path):
        """Check if a file exists (relative to plugin dir)."""
        try:
            return os.path.exists(self._safe_path(str(path)))
        except Exception:
            return False

    def _safe_path(self, path: str) -> str:
        """Resolve *path* inside the plugin directory; raise on escape."""
        full = os.path.normpath(os.path.join(self._plugin_dir, path))
        if not full.startswith(os.path.normpath(self._plugin_dir)):
            raise PermissionError(f"Path escapes plugin sandbox: {path}")
        return full

    # -- Config -------------------------------------------------------------

    def get_config(self, key):
        """Get a plugin-specific config value set by the user."""
        value = self._meta.config_values.get(str(key))
        # Cast floats to int for fields declared as type="number" in config_schema
        if isinstance(value, float) and value == int(value):
            schema = self._meta.config_schema or []
            for field in schema:
                if field.get("key") == str(key) and field.get("type") == "number":
                    return int(value)
        return value

    def get_all_config(self):
        """Get all plugin config values as a Lua table."""
        return _python_to_lua(self._lua, self._meta.config_values)

    # -- Utilities ----------------------------------------------------------

    def hash(self, text, algorithm="sha256"):
        """Hash a string with the given algorithm."""
        text = str(text).encode("utf-8")
        algorithm = str(algorithm).lower()
        try:
            h = hashlib.new(algorithm, text)
            return h.hexdigest()
        except ValueError as e:
            return None, str(e)

    def base64_encode(self, text):
        return base64.b64encode(str(text).encode("utf-8")).decode("ascii")

    def base64_decode(self, text):
        try:
            return base64.b64decode(str(text)).decode("utf-8")
        except Exception as e:
            return None, str(e)

    def url_encode(self, text):
        return urllib.parse.quote(str(text), safe="")

    def url_decode(self, text):
        return urllib.parse.unquote(str(text))

    def sleep(self, seconds):
        """Sleep for N seconds (use sparingly)."""
        time.sleep(max(0, min(float(seconds), 60)))

    def get_tool_version(self):
        return TOOL_VERSION

    def get_platform(self):
        import platform
        return platform.system()

    # -- Cache (in-memory, per-session) -------------------------------------

    def cache_get(self, key):
        return self._cache.get(str(key))

    def cache_set(self, key, value):
        self._cache[str(key)] = value

    def cache_clear(self):
        self._cache.clear()

    # -- Graph API ----------------------------------------------------------

    def graph_create(self, name=None, direction=None):
        """Create a new graph. Returns graph id (string)."""
        gid = f"G{uuid.uuid4().hex[:8]}"
        g = Graph(
            name=_lua_str(name) if name else f"Graph_{self._meta.id}",
            direction=_lua_str(direction) if direction else "TD",
        )
        if not hasattr(self, '_graphs'):
            self._graphs: dict[str, Graph] = {}
        self._graphs[gid] = g
        self._output(f"[Graph] Created graph '{g.name}' (id={gid})")
        return gid

    def graph_add_node(self, graph_id, label, node_type=None, shape=None,
                       style=None, description=None, metadata_table=None):
        """Add a node to a graph. Returns node id."""
        g = self._get_graph(graph_id)
        if g is None:
            return None, f"Graph '{graph_id}' not found"

        ntype = _lua_str(node_type) if node_type else "Custom"
        node = Node.from_type(_lua_str(label), ntype)

        if shape:
            node.mermaid_shape = _lua_str(shape)
        if style:
            node.mermaid_style = _lua_str(style)
        if description:
            node.description = _lua_str(description)
        if metadata_table:
            node.metadata = _lua_table_to_dict(metadata_table)

        g.add_node(node)
        return node.id

    def graph_add_edge(self, graph_id, source_id, target_id, label=None,
                       edge_type=None, line_type=None, style=None,
                       metadata_table=None):
        """Add an edge between two nodes. Returns edge id."""
        g = self._get_graph(graph_id)
        if g is None:
            return None, f"Graph '{graph_id}' not found"

        edge = Edge(
            source_id=_lua_str(source_id),
            target_id=_lua_str(target_id),
            label=_lua_str(label) if label else "",
            edge_type=_lua_str(edge_type) if edge_type else "Connected",
            mermaid_line=_lua_str(line_type) if line_type else "-->",
            mermaid_style=_lua_str(style) if style else "",
        )
        if metadata_table:
            edge.metadata = _lua_table_to_dict(metadata_table)

        if not g.add_edge(edge):
            return None, f"Source or target node not found"
        return edge.id

    def graph_find_node(self, graph_id, label):
        """Find a node by its label. Returns node id or nil."""
        g = self._get_graph(graph_id)
        if g is None:
            return None
        for n in g.nodes:
            if n.label == _lua_str(label):
                return n.id
        return None

    def graph_get_nodes(self, graph_id):
        """Return all node ids and labels as a Lua table."""
        g = self._get_graph(graph_id)
        if g is None:
            return None
        result = {}
        for i, n in enumerate(g.nodes, 1):
            result[i] = {"id": n.id, "label": n.label, "type": n.node_type}
        return _python_to_lua(self._lua, result)

    def graph_save(self, graph_id, filename=None):
        """Save the graph to a JSON file in the plugin directory. Returns filepath."""
        g = self._get_graph(graph_id)
        if g is None:
            return None, f"Graph '{graph_id}' not found"

        if not filename:
            safe_name = g.name.replace(" ", "_").replace("/", "_").replace("\\", "_")
            filename = f"{safe_name}.graph.json"

        filepath = self._safe_path(_lua_str(filename))
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        g.save_json(filepath)
        self._output(f"[Graph] Saved → {filepath}")

        # Store path for the host to pick up
        if not hasattr(self, '_saved_graph_paths'):
            self._saved_graph_paths: list[str] = []
        self._saved_graph_paths.append(filepath)

        return filepath

    def graph_set_direction(self, graph_id, direction):
        """Set graph direction: TD, LR, RL, BT."""
        g = self._get_graph(graph_id)
        if g is None:
            return None, f"Graph '{graph_id}' not found"
        g.direction = _lua_str(direction)
        return True

    def graph_node_set_style(self, graph_id, node_id, style):
        """Override the CSS style of a node."""
        g = self._get_graph(graph_id)
        if g is None:
            return None
        node = g.get_node(_lua_str(node_id))
        if node is None:
            return None
        node.mermaid_style = _lua_str(style)
        return True

    def graph_node_set_shape(self, graph_id, node_id, shape):
        """Override the shape of a node (rect, round, circle, diamond, hexagon)."""
        g = self._get_graph(graph_id)
        if g is None:
            return None
        node = g.get_node(_lua_str(node_id))
        if node is None:
            return None
        node.mermaid_shape = _lua_str(shape)
        return True

    def graph_get_node_types(self):
        """Return available node types and their default styles as a Lua table."""
        return _python_to_lua(self._lua, NODE_TYPE_DEFAULTS)

    def _get_graph(self, graph_id) -> Optional[Graph]:
        if not hasattr(self, '_graphs'):
            return None
        return self._graphs.get(_lua_str(graph_id))

    # -- Username OSINT API ------------------------------------------------

    def username_search(self, username, categories=None, max_workers=30):
        """Search username across sites. Returns results as Lua table.

        Usage in Lua::

            local results = host:username_search("johndoe")
            -- or with category filter:
            local results = host:username_search("johndoe", {"social", "gaming"})
        """
        from script.tools.username_osint.site_db import SiteDB
        from script.tools.username_osint.checker import UsernameChecker

        db = SiteDB()
        sites = db.load()
        if categories and hasattr(categories, 'values'):
            cat_list = [_lua_str(v) for v in categories.values()]
            sites = db.filter_by_category(cat_list)

        self._output(f"[Username OSINT] Checking '{_lua_str(username)}' on {len(sites)} sites...")

        def _progress(checked, total, result):
            if result.status == "found":
                self._output(f"  [+] {result.site_name}: {result.url}")

        checker = UsernameChecker(
            sites, max_workers=int(max_workers),
            progress_callback=_progress,
        )
        results = checker.check_username(_lua_str(username))

        # Convert to Lua table
        out = {}
        for i, r in enumerate([x for x in results if x.status == "found"], 1):
            out[i] = {
                "site": r.site_name,
                "url": r.url,
                "category": r.category,
                "http_code": r.http_code or 0,
                "response_ms": round(r.response_time_ms),
            }
            if r.avatar_url:
                out[i]["avatar_url"] = r.avatar_url

        self._output(f"[Username OSINT] Found {len(out)} accounts.")
        return _python_to_lua(self._lua, out)

    def username_generate_nicks(self, username, max_variants=100,
                                 first_name=None, last_name=None):
        """Generate forensic nickname variants. Returns Lua table of strings.

        Usage in Lua::

            local nicks = host:username_generate_nicks("johndoe", 50)
            for i, nick in ipairs(nicks) do print(nick) end
        """
        from script.tools.username_osint.nickname_generator import NicknameGenerator

        gen = NicknameGenerator(_lua_str(username), max_variants=int(max_variants))
        variants = gen.generate_all(
            first_name=_lua_str(first_name) if first_name else "",
            last_name=_lua_str(last_name) if last_name else "",
        )

        self._output(f"[Nickname Gen] Generated {len(variants)} variants for '{_lua_str(username)}'")
        return _python_to_lua(self._lua, variants)

    def username_search_to_graph(self, graph_id, username, categories=None):
        """Search username and auto-populate a graph with results.

        Usage in Lua::

            local gid = host:graph_create("OSINT Graph")
            host:username_search_to_graph(gid, "johndoe")
        """
        from script.tools.username_osint.site_db import SiteDB
        from script.tools.username_osint.checker import UsernameChecker
        from script.tools.username_osint.models import CATEGORY_ICONS

        g = self._get_graph(graph_id)
        if g is None:
            return None, f"Graph '{graph_id}' not found"

        uname = _lua_str(username)

        # Run search
        db = SiteDB()
        sites = db.load()
        if categories and hasattr(categories, 'values'):
            cat_list = [_lua_str(v) for v in categories.values()]
            sites = db.filter_by_category(cat_list)

        self._output(f"[Username→Graph] Checking '{uname}' on {len(sites)} sites...")
        checker = UsernameChecker(sites, max_workers=30)
        results = checker.check_username(uname)
        found = [r for r in results if r.status == "found"]

        if not found:
            self._output(f"[Username→Graph] No accounts found for '{uname}'.")
            return 0

        # Build graph nodes
        central = Node.from_type(f"@{uname}", "Username")
        g.add_node(central)

        cat_nodes = {}
        for r in found:
            cat = r.category
            if cat not in cat_nodes:
                icon = CATEGORY_ICONS.get(cat, "")
                cn = Node.from_type(f"{icon} {cat.capitalize()}", "Category")
                g.add_node(cn)
                g.add_edge(Edge(central.id, cn.id, label=cat, edge_type="BelongsToCategory"))
                cat_nodes[cat] = cn

            sn = Node.from_type(r.site_name, "SocialAccount")
            sn.description = r.url
            sn.metadata = {"url": r.url}
            g.add_node(sn)
            g.add_edge(Edge(cat_nodes[cat].id, sn.id, label="registered", edge_type="RegisteredOn"))

        self._output(f"[Username→Graph] Added {len(found)} sites + {len(cat_nodes)} categories to graph.")
        return len(found)


# ---------------------------------------------------------------------------
# Helpers  –  Lua <-> Python conversion
# ---------------------------------------------------------------------------

def _lua_str(value) -> str:
    """Safely convert a Lua value (may be bytes) to a Python str."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _lua_table_to_dict(tbl) -> dict:
    """Convert a Lua table to a Python dict (shallow, bytes-safe)."""
    if tbl is None:
        return {}
    result = {}
    try:
        for k, v in tbl.items():
            result[_lua_str(k)] = _lua_str(v) if isinstance(v, bytes) else v
    except Exception:
        pass
    return result


def _lua_table_to_python(obj):
    """Recursively convert Lua tables to Python dicts/lists."""
    if obj is None:
        return None
    if hasattr(obj, 'items'):
        # Check if it's a sequence (1-based integer keys)
        d = {}
        is_array = True
        max_idx = 0
        for k, v in obj.items():
            d[k] = _lua_table_to_python(v)
            if isinstance(k, (int, float)) and int(k) == k and int(k) >= 1:
                max_idx = max(max_idx, int(k))
            else:
                is_array = False
        if is_array and max_idx == len(d) and max_idx > 0:
            return [d[i] for i in range(1, max_idx + 1)]
        return {_lua_str(k): v for k, v in d.items()}
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    return obj


def _python_to_lua(lua, obj):
    """Convert a Python dict/list/scalar to a Lua table."""
    if isinstance(obj, dict):
        tbl = lua.table()
        for k, v in obj.items():
            tbl[k] = _python_to_lua(lua, v)
        return tbl
    if isinstance(obj, (list, tuple)):
        tbl = lua.table()
        for i, v in enumerate(obj, 1):
            tbl[i] = _python_to_lua(lua, v)
        return tbl
    if isinstance(obj, bool):
        return obj
    return obj


# ---------------------------------------------------------------------------
# Sandbox builder
# ---------------------------------------------------------------------------

def _create_sandbox_env(lua: 'LuaRuntime', host: HostAPI):
    """
    Build a restricted global environment for a Lua plugin.

    Only safe built-in functions are exposed. Dangerous modules
    (io, os, debug, loadfile, dofile) are NOT available.
    """
    sandbox_code = """
    function(host_obj)
        local env = {
            -- safe builtins
            print     = function(...) host_obj:print(...) end,
            type      = type,
            tostring  = tostring,
            tonumber  = tonumber,
            pairs     = pairs,
            ipairs    = ipairs,
            next      = next,
            select    = select,
            unpack    = unpack or table.unpack,
            pcall     = pcall,
            xpcall    = xpcall,
            error     = error,
            assert    = assert,
            rawget    = rawget,
            rawset    = rawset,
            rawequal  = rawequal,
            setmetatable = setmetatable,
            getmetatable = getmetatable,

            -- safe modules
            string    = string,
            table     = table,
            math      = math,

            -- host API
            host = host_obj,
        }
        env._G = env
        return env
    end
    """
    make_env = lua.eval(sandbox_code)
    return make_env(host)


# ---------------------------------------------------------------------------
# Plugin loader
# ---------------------------------------------------------------------------

def _load_plugin_meta(filepath: str) -> Optional[LuaPluginMeta]:
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
        with open(filepath, "r", encoding="utf-8") as f:
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


def discover_lua_plugins(base_dir: str = LUA_PLUGIN_DIR) -> list[LuaPluginMeta]:
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


# ---------------------------------------------------------------------------
# Plugin settings persistence
# ---------------------------------------------------------------------------

def load_lua_plugin_settings() -> dict:
    """Load saved plugin enable/disable state and config values."""
    if os.path.exists(LUA_PLUGIN_CONFIG_FILE):
        try:
            with open(LUA_PLUGIN_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_lua_plugin_settings(settings: dict):
    with open(LUA_PLUGIN_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)


def apply_settings_to_plugins(plugins: list[LuaPluginMeta], settings: dict):
    """Apply saved settings (enabled state, config values) to loaded plugins."""
    for p in plugins:
        ps = settings.get(p.id, {})
        p.enabled = ps.get("enabled", True)
        p.config_values = ps.get("config", {})


# ---------------------------------------------------------------------------
# Plugin executor
# ---------------------------------------------------------------------------

def run_lua_plugin(plugin: LuaPluginMeta, function_name: str, query: str = "",
                   options: dict = None,
                   output_callback: Callable[[str], None] = None,
                   graph_callback: Callable[[str], None] = None) -> Optional[str]:
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
        with open(plugin.filepath, "r", encoding="utf-8") as f:
            source = f.read()

        # Load and execute the plugin source inside the sandbox
        loader = lua.eval("""
        function(source, env)
            local fn, err = load(source, "%s", "t", env)
            if not fn then error(err) end
            return fn()
        end
        """ % plugin.id)

        plugin_table = loader(source, env)

        if plugin_table is None or not hasattr(plugin_table, '__getitem__'):
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
        if graph_callback and hasattr(host, '_saved_graph_paths'):
            for gpath in host._saved_graph_paths:
                graph_callback(gpath)

        # Handle nil, error return pattern
        if result is None:
            return None

        # If result is a Lua table, convert and JSON-encode for display
        if hasattr(result, 'items'):
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
