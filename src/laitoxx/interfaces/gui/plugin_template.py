"""
Lua Plugin Builder - code editor with syntax highlighting, code snippets,
syntax checking, and OS-dependent template generation.
"""

import re

# ============================================================================
# Lua Syntax Highlighter
# ============================================================================


def generate_plugin_template(
    plugin_name: str,
    plugin_type: str,
    author: str,
    description: str,
    target_os: list[str],
) -> str:
    """Generate a Lua plugin template based on metadata and target OS."""

    os_comment = ""
    os_check = ""
    if target_os:
        os_list = ", ".join(f'"{o}"' for o in target_os)
        os_comment = f"-- Target OS: {', '.join(target_os)}\n"
        if len(target_os) < 3:
            os_check = f"""
    -- OS check
    local platform = host:get_platform()
    local supported = {{ {os_list} }}
    local ok = false
    for _, os_name in ipairs(supported) do
        if platform:lower():find(os_name:lower()) then ok = true; break end
    end
    if not ok then
        return nil, "This plugin only supports: " .. table.concat(supported, ", ")
    end
"""

    safe_id = re.sub(r"[^a-zA-Z0-9_]", "_", plugin_name).lower()

    func_name = {
        "search": "search",
        "processor": "process",
        "formatter": "format",
        "passive_scanner": "scan",
    }.get(plugin_type, "search")

    func_param = {
        "search": "query",
        "processor": "data",
        "formatter": "data",
        "passive_scanner": "target",
    }.get(plugin_type, "query")

    func_body = (
        os_check
        + f'''
    if not {func_param} or {func_param} == "" then
        return nil, "Input cannot be empty."
    end

    host:print("Running {plugin_name}...")
    host:print("Input: " .. {func_param})

    -- TODO: Add your logic here

    return "Done!"'''
    )

    # For search type, also add the search alias
    extra_func = ""
    if plugin_type == "processor":
        extra_func = "\n-- Alias: also works when called as 'search'\nplugin.search = plugin.process\n"
    elif plugin_type == "formatter":
        extra_func = "\n-- Alias: also works when called as 'search'\nplugin.search = plugin.format\n"
    elif plugin_type == "passive_scanner":
        extra_func = "\n-- Alias: also works when called as 'search'\nplugin.search = plugin.scan\n"

    return f'''{os_comment}local plugin = {{
    id          = "{safe_id}",
    name        = "{plugin_name}",
    description = "{description}",
    author      = "{author}",
    version     = "1.0",
    type        = "{plugin_type}",

    -- User-configurable settings (shown in plugin settings UI)
    config_schema = {{
        -- {{ key = "api_key", label = "API Key", type = "string", default = "" }},
    }},
}}

function plugin.{func_name}({func_param}, options){func_body}
end
{extra_func}
return plugin
'''
