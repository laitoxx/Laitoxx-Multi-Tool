# Керівництво з розробки плагінів / Plugin Development Guide
*Примітка: Переклад цього документу наразі в процесі. Нижче наведено оригінальну англійську версію.*

# Plugin Development Guide / Руководство по разработке плагинов

---

## English

### Getting Started

Laitoxx plugins are written in **Lua** and run inside a secure sandbox. Each plugin is a single `.lua` file placed in the `lua_plugins/` directory. The application discovers plugins automatically on startup.

**Quick start:**
1. Open the **Plugin Builder** from the sidebar
2. Fill in metadata (name, author, description, type, target OS)
3. Write your code using the built-in editor with syntax highlighting
4. Save — your plugin appears in the **Plugins** category immediately

Or manually: copy `lua_plugins/_template.lua`, rename it, edit, restart the app.

> Files starting with `_` (like `_template.lua`) are ignored by the plugin loader.

---

### Plugin Structure

Every plugin must return a table with metadata and at least one handler function:

```lua
local plugin = {
    id          = "my_plugin",        -- Unique ID (no spaces, lowercase)
    name        = "My Plugin",        -- Display name in the UI
    description = "What it does.",     -- Shown in tooltip
    author      = "Your Name",
    version     = "1.0",
    type        = "search",           -- "search" | "processor" | "formatter" | "passive_scanner"

    -- Optional: user-configurable settings
    config_schema = {
        { key = "api_key",     label = "API Key",     type = "string",  default = "" },
        { key = "max_results", label = "Max Results",  type = "number",  default = 10 },
        { key = "verbose",     label = "Verbose Mode", type = "boolean", default = false },
    },
}

function plugin.search(query, options)
    -- Your logic here
    return "result string"
end

return plugin  -- IMPORTANT: always return the plugin table
```

---

### Plugin Types

| Type | Primary function | Use case |
|------|-----------------|----------|
| `search` | `plugin.search(query, options)` | Query external APIs, databases, OSINT sources |
| `processor` | `plugin.process(data, options)` | Transform, enrich, or analyze data |
| `formatter` | `plugin.format(data, options)` | Export results to CSV, JSON, custom formats |
| `passive_scanner` | `plugin.scan(target, options)` | Analyze input without active network requests |

> Tip: you can define multiple functions. For example, a processor plugin can also define `plugin.search` as an alias.

---

### Host API Reference

All host functions are called with colon syntax: `host:method(args)`.

#### Output

| Function | Description |
|----------|-------------|
| `host:print(...)` | Print text to the plugin output (shown in UI) |
| `host:log(message, level)` | Log to app log + output. Levels: `"info"`, `"warn"`, `"error"`, `"debug"` |

#### HTTP Requests

| Function | Description |
|----------|-------------|
| `host:http_get(url, timeout, headers)` | GET request. Returns `body` or `nil, error` |
| `host:http_post(url, data, timeout, headers, content_type)` | POST request. Returns `body` or `nil, error` |

```lua
-- GET example
local body, err = host:http_get("https://api.example.com/data?q=" .. host:url_encode(query), 15)
if not body then
    return nil, "Request failed: " .. (err or "unknown")
end

-- POST example with JSON
local payload = host:json_encode({ query = query, limit = 10 })
local body, err = host:http_post("https://api.example.com/search", payload, 15)
```

#### JSON

| Function | Description |
|----------|-------------|
| `host:json_decode(string)` | Parse JSON string into a Lua table. Returns `table` or `nil, error` |
| `host:json_encode(table)` | Convert Lua table to JSON string. Returns `string` or `nil, error` |

```lua
local data, err = host:json_decode(body)
if not data then
    return nil, "JSON parse error: " .. (err or "unknown")
end

-- Access fields
host:print("Name: " .. tostring(data.name))
host:print("Count: " .. tostring(data.results))
```

#### File System (Sandboxed)

All file operations are restricted to the plugin's own directory. Path traversal is blocked.

| Function | Description |
|----------|-------------|
| `host:read_file(path)` | Read file contents. Returns `string` or `nil, error` |
| `host:write_file(path, content)` | Write content to file. Returns `true` or `nil, error` |
| `host:file_exists(path)` | Check if file exists. Returns `boolean` |

```lua
-- Save results to a file inside plugin directory
host:write_file("last_results.json", host:json_encode(results))

-- Read cached data
local cached = host:read_file("cache.json")
if cached then
    local data = host:json_decode(cached)
end
```

#### Configuration

| Function | Description |
|----------|-------------|
| `host:get_config(key)` | Get a single config value set by the user |
| `host:get_all_config()` | Get all config values as a table |

```lua
local api_key = host:get_config("api_key")
if not api_key or api_key == "" then
    return nil, "Please set your API key in plugin settings (right-click the plugin)."
end
```

#### Utilities

| Function | Description |
|----------|-------------|
| `host:hash(text, algorithm)` | Hash text. Algorithms: `"md5"`, `"sha1"`, `"sha256"`, `"sha512"`, etc. |
| `host:base64_encode(text)` | Base64 encode |
| `host:base64_decode(text)` | Base64 decode. Returns `string` or `nil, error` |
| `host:url_encode(text)` | URL-encode (percent encoding) |
| `host:url_decode(text)` | URL-decode |
| `host:sleep(seconds)` | Pause execution (max 60 seconds) |
| `host:get_tool_version()` | Returns Laitoxx version string |
| `host:get_platform()` | Returns `"Windows"`, `"Linux"`, or `"Darwin"` |

#### Cache (In-Memory, Per Session)

| Function | Description |
|----------|-------------|
| `host:cache_get(key)` | Get a cached value (lost on app restart) |
| `host:cache_set(key, value)` | Set a cached value |
| `host:cache_clear()` | Clear all cached values |

#### Graph API

Plugins can build interactive graphs (node-link diagrams) that open in the built-in Graph Editor. When your plugin calls `host:graph_save()`, the user is prompted to view the graph.

| Function | Description |
|----------|-------------|
| `host:graph_create(name, direction)` | Create a new graph. `direction`: `"TD"`, `"LR"`, `"RL"`, `"BT"`. Returns `graph_id` |
| `host:graph_add_node(gid, label, node_type, shape, style, description)` | Add a node. Returns `node_id` or `nil, error` |
| `host:graph_add_edge(gid, src_id, tgt_id, label, edge_type, line_type, style)` | Add an edge. Returns `edge_id` or `nil, error` |
| `host:graph_find_node(gid, label)` | Find a node by label. Returns `node_id` or `nil` |
| `host:graph_get_nodes(gid)` | Get all nodes as a table of `{id, label, type}` |
| `host:graph_save(gid, filename)` | Save graph to JSON file. Returns `filepath` or `nil, error`. **Triggers the "Open graph?" prompt** |
| `host:graph_set_direction(gid, direction)` | Change graph direction |
| `host:graph_node_set_style(gid, node_id, style)` | Override node CSS style |
| `host:graph_node_set_shape(gid, node_id, shape)` | Override node shape |
| `host:graph_get_node_types()` | Get available node types and their default styles |

**Node types:** `"Person"`, `"Email"`, `"Phone"`, `"Website"`, `"Company"`, `"IP"`, `"Address"`, `"Document"`, `"Custom"`

**Shapes:** `"rect"`, `"round"`, `"circle"`, `"diamond"`, `"hexagon"`, `"flag"`, `"trapez"`

**Line types:** `"-->"` (arrow), `"==>"` (thick), `"-.->"` (dotted), `"---"` (open), `"<-->"` (double)

**Style** is a CSS string, e.g.: `"fill:#FFD700,stroke:#8B4513,stroke-width:2px,color:#000"`

```lua
-- Graph API example
local gid = host:graph_create("My Investigation", "LR")

-- Add nodes with custom styles
local n1 = host:graph_add_node(gid, "John Doe", "Person", "round",
    "fill:#FFD700,stroke:#8B4513,stroke-width:2px,color:#000", "Main target")
local n2 = host:graph_add_node(gid, "john@example.com", "Email", "rect",
    "fill:#ADD8E6,stroke:#1E90FF,stroke-width:2px,color:#000")
local n3 = host:graph_add_node(gid, "+7-999-123-4567", "Phone", "rect",
    "fill:#98FB98,stroke:#228B22,stroke-width:2px,color:#000")

-- Add edges with labels
host:graph_add_edge(gid, n1, n2, "personal email", "Connected", "-->")
host:graph_add_edge(gid, n1, n3, "mobile", "Connected", "-->")

-- Save — user will be asked "Open in Graph Editor?"
host:graph_save(gid, "investigation.graph.json")
```

> **Tip:** Define a `graph_styles` table in your plugin to keep all color/shape definitions in one place. See the LeakOSINT plugin for a complete example with auto-detection of data types.

---

### Error Handling

Use the `nil, "error message"` pattern to signal errors:

```lua
function plugin.search(query, options)
    if not query or query == "" then
        return nil, "Query cannot be empty."
    end

    local body, err = host:http_get(url, 10)
    if not body then
        return nil, "HTTP request failed: " .. (err or "unknown error")
    end

    -- For safe execution of risky code:
    local ok, result = pcall(function()
        -- code that might fail
        return some_operation()
    end)
    if not ok then
        host:log("Internal error: " .. tostring(result), "error")
        return nil, "Something went wrong."
    end

    return result
end
```

---

### Return Values

Your handler function can return:

| Return type | What happens |
|-------------|-------------|
| `string` | Displayed directly in the output area |
| `table` | Automatically converted to formatted JSON |
| `nil` | Nothing displayed (use `host:print()` for output instead) |
| `nil, "error"` | Error message displayed to the user |

---

### Config Schema

Define `config_schema` in your plugin table to let users configure settings via the UI (right-click → Plugin Settings):

```lua
config_schema = {
    { key = "api_key",     label = "API Key",        type = "string",  default = "" },
    { key = "timeout",     label = "Timeout (sec)",   type = "number",  default = 15 },
    { key = "show_raw",    label = "Show Raw Data",   type = "boolean", default = false },
}
```

Supported types: `"string"`, `"number"`, `"boolean"`.

Access values with `host:get_config("key_name")`.

---

### OS-Specific Plugins

If your plugin only works on certain operating systems:

```lua
function plugin.search(query, options)
    local platform = host:get_platform()
    if platform ~= "Windows" then
        return nil, "This plugin only works on Windows."
    end
    -- Windows-specific logic
end
```

The Plugin Builder can generate this check automatically when you select target OS.

---

### Sandbox Rules

Plugins run in a restricted environment. The following is **available**:

- `print`, `type`, `tostring`, `tonumber`
- `pairs`, `ipairs`, `next`, `select`, `unpack`
- `pcall`, `xpcall`, `error`, `assert`
- `rawget`, `rawset`, `rawequal`
- `setmetatable`, `getmetatable`
- `string.*`, `table.*`, `math.*`
- All `host:*` functions

The following is **NOT available** (blocked for security):

- `io`, `os`, `debug` modules
- `loadfile`, `dofile`, `load` (except internal use)
- `require`
- Direct file system access
- Network access (use `host:http_get/post` instead)

---

### Best Practices

1. **Always validate input** — check that `query` is not nil or empty
2. **Handle HTTP errors** — always check the second return value
3. **Use `host:print()`** for progress updates during long operations
4. **Keep plugins focused** — one plugin, one purpose
5. **Use `config_schema`** for API keys instead of hardcoding them
6. **Use `local`** for all variables to avoid polluting the sandbox
7. **Return meaningful errors** — tell the user what went wrong and how to fix it
8. **Use `host:cache_set/get`** to avoid redundant API calls within a session
9. **Respect rate limits** — use `host:sleep()` between rapid API calls
10. **Test with the syntax checker** — press "Check Syntax" before saving

---

### Complete Example: API Search Plugin

```lua
local plugin = {
    id          = "shodan_search",
    name        = "Shodan Search",
    description = "Search Shodan for hosts and services.",
    author      = "Community",
    version     = "1.0",
    type        = "search",

    config_schema = {
        { key = "api_key", label = "Shodan API Key", type = "string", default = "" },
    },
}

function plugin.search(query, options)
    if not query or query == "" then
        return nil, "Enter an IP address or search query."
    end

    local api_key = host:get_config("api_key")
    if not api_key or api_key == "" then
        return nil, "Shodan API key required. Right-click this plugin → Plugin Settings."
    end

    host:print("Searching Shodan for: " .. query)

    local url = "https://api.shodan.io/shodan/host/" .. host:url_encode(query)
        .. "?key=" .. host:url_encode(api_key)

    local body, err = host:http_get(url, 15)
    if not body then
        return nil, "Shodan request failed: " .. (err or "unknown error")
    end

    local data, err = host:json_decode(body)
    if not data then
        return nil, "Failed to parse response: " .. (err or "unknown")
    end

    if data.error then
        return nil, "Shodan error: " .. tostring(data.error)
    end

    local lines = {
        "=== Shodan Results ===",
        "",
        "IP:       " .. tostring(data.ip_str or query),
        "Org:      " .. tostring(data.org or "N/A"),
        "OS:       " .. tostring(data.os or "N/A"),
        "Ports:    " .. table.concat(data.ports or {}, ", "),
        "Country:  " .. tostring(data.country_name or "N/A"),
        "City:     " .. tostring(data.city or "N/A"),
        "",
    }

    if data.data then
        lines[#lines + 1] = "Services:"
        for i, svc in ipairs(data.data) do
            lines[#lines + 1] = string.format(
                "  %d/%-5s %s",
                svc.port or 0,
                tostring(svc.transport or "tcp"),
                tostring(svc.product or svc.module or "unknown")
            )
            if i >= 20 then
                lines[#lines + 1] = "  ... (truncated)"
                break
            end
        end
    end

    lines[#lines + 1] = ""
    lines[#lines + 1] = "======================"
    return table.concat(lines, "\n")
end

return plugin
```

---
---