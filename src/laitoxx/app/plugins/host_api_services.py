"""
Lua Plugin Engine for Laitoxx.

Uses `lupa` (LuaJIT/Lua runtime for Python) to execute Lua plugins
inside a sandboxed environment with a rich host API.
"""

import base64
import hashlib
import json
import logging
import os
import ssl
import time
import urllib.parse

from requests.adapters import HTTPAdapter

from laitoxx import __version__

try:
    import truststore
except ImportError:
    truststore = None

from .lua_values import _lua_str, _lua_table_to_dict, _lua_table_to_python, _python_to_lua


class _SystemTrustAdapter(HTTPAdapter):
    """Use the OS certificate store while preserving normal TLS verification."""

    def __init__(self, *args, **kwargs):
        self._ssl_context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT) if truststore is not None else None
        super().__init__(*args, **kwargs)

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        if self._ssl_context is not None:
            pool_kwargs.setdefault("ssl_context", self._ssl_context)
        return super().init_poolmanager(connections, maxsize, block=block, **pool_kwargs)

    def proxy_manager_for(self, proxy, **proxy_kwargs):
        if self._ssl_context is not None:
            proxy_kwargs.setdefault("ssl_context", self._ssl_context)
        return super().proxy_manager_for(proxy, **proxy_kwargs)


def apply_system_trust(session):
    """Mount system-trust TLS support when the optional dependency is available."""
    if truststore is not None:
        session.mount("https://", _SystemTrustAdapter())
    return session


class ServiceHostMixin:
    def _output(self, msg):
        """Output with bytes-safe conversion."""
        if isinstance(msg, bytes):
            msg = msg.decode("utf-8", errors="replace")
        self._raw_output(str(msg))

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

    def http_get(self, url, timeout=15, headers_table=None):
        """Perform an HTTP GET request. Returns body string or nil+error."""
        try:
            headers = _lua_table_to_dict(headers_table) if headers_table else {}
            resp = self._session.get(str(url), timeout=int(timeout), headers=headers)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            return None, str(e)

    def http_post(
        self,
        url,
        data=None,
        timeout=15,
        headers_table=None,
        content_type="application/json",
    ):
        """Perform an HTTP POST request. Returns body string or nil+error."""
        try:
            headers = _lua_table_to_dict(headers_table) if headers_table else {}
            headers.setdefault("Content-Type", str(content_type))
            body = data
            if hasattr(data, "keys"):
                body = json.dumps(_lua_table_to_dict(data), ensure_ascii=False)
            if isinstance(body, str):
                body = body.encode("utf-8")
            resp = self._session.post(str(url), data=body, timeout=int(timeout), headers=headers)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            return None, str(e)

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

    def read_file(self, path):
        """Read a file relative to the plugin directory."""
        try:
            full = self._safe_path(str(path))
            with open(full, encoding="utf-8") as f:
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
        return __version__

    def get_platform(self):
        import platform

        return platform.system()

    def cache_get(self, key):
        return self._cache.get(str(key))

    def cache_set(self, key, value):
        self._cache[str(key)] = value

    def cache_clear(self):
        self._cache.clear()
