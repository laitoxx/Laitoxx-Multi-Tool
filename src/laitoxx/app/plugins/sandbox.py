"""Restricted Lua execution environment construction."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lupa import LuaRuntime

    from .engine import HostAPI


def _create_sandbox_env(lua: LuaRuntime, host: HostAPI):
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
