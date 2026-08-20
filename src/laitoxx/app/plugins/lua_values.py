"""Conversions between Lua tables and ordinary Python values."""


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
    if hasattr(obj, "items"):
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
