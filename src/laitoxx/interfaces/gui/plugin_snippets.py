"""Lua snippets and authoring tips."""

CODE_SNIPPETS = {
    "http_get": {
        "label": "HTTP GET Request",
        "description": "Make an HTTP GET request and parse JSON response",
        "fields": [
            {
                "key": "url",
                "label": "URL",
                "placeholder": "https://api.example.com/endpoint",
            },
        ],
        "template": """
    local body, err = host:http_get("{url}", 15)
    if not body then
        host:print("Request failed: " .. (err or "unknown error"))
        return nil, err
    end
    host:print("Response received: " .. #body .. " bytes")
""",
    },
    "http_post": {
        "label": "HTTP POST Request",
        "description": "Make an HTTP POST request with JSON body",
        "fields": [
            {
                "key": "url",
                "label": "URL",
                "placeholder": "https://api.example.com/endpoint",
            },
            {
                "key": "body_desc",
                "label": "Body description",
                "placeholder": "key = value, ...",
            },
        ],
        "template": """
    local post_data = host:json_encode({{ {body_desc} }})
    local body, err = host:http_post("{url}", post_data, 15)
    if not body then
        host:print("POST failed: " .. (err or "unknown error"))
        return nil, err
    end
    host:print("POST response: " .. #body .. " bytes")
""",
    },
    "json_parse": {
        "label": "Parse JSON Response",
        "description": "Decode a JSON string into a Lua table",
        "fields": [],
        "template": """
    local data, err = host:json_decode(body)
    if not data then
        return nil, "JSON parse error: " .. (err or "unknown")
    end
""",
    },
    "http_get_json": {
        "label": "GET + Parse JSON (Full)",
        "description": "Complete HTTP GET with JSON parsing and error handling",
        "fields": [
            {
                "key": "url",
                "label": "URL",
                "placeholder": "https://api.example.com/search?q=",
            },
            {"key": "query_param", "label": "Append query?", "placeholder": "yes"},
        ],
        "template": """
    local url = "{url}"
    if query and query ~= "" then
        url = url .. host:url_encode(query)
    end

    local body, err = host:http_get(url, 15)
    if not body then
        return nil, "HTTP error: " .. (err or "unknown")
    end

    local data, err = host:json_decode(body)
    if not data then
        return nil, "JSON parse error: " .. (err or "unknown")
    end

    host:print("Got " .. tostring(#data) .. " results")
""",
    },
    "config_check": {
        "label": "Check Config Value",
        "description": "Read and validate a user-configured API key",
        "fields": [
            {"key": "config_key", "label": "Config key", "placeholder": "api_key"},
        ],
        "template": """
    local api_key = host:get_config("{config_key}")
    if not api_key or api_key == "" then
        return nil, "Please configure '{config_key}' in plugin settings."
    end
""",
    },
    "format_output": {
        "label": "Format Output Lines",
        "description": "Build formatted output with multiple lines",
        "fields": [],
        "template": """
    local lines = {}
    lines[#lines + 1] = "=== Results ==="
    lines[#lines + 1] = ""
    -- Add your formatted lines here:
    -- lines[#lines + 1] = "Key:   " .. tostring(value)
    lines[#lines + 1] = ""
    lines[#lines + 1] = "==============="
    return table.concat(lines, "\\n")
""",
    },
    "error_handling": {
        "label": "Error Handling (pcall)",
        "description": "Wrap code in pcall for safe execution",
        "fields": [],
        "template": """
    local ok, result = pcall(function()
        -- Your code here
        return "success"
    end)
    if not ok then
        host:log("Error: " .. tostring(result), "error")
        return nil, "Internal error: " .. tostring(result)
    end
""",
    },
    "file_cache": {
        "label": "File-based Cache",
        "description": "Cache results to a file in the plugin directory",
        "fields": [
            {
                "key": "cache_file",
                "label": "Cache filename",
                "placeholder": "cache.json",
            },
        ],
        "template": """
    -- Try to read from cache
    local cached = host:read_file("{cache_file}")
    if cached then
        local data = host:json_decode(cached)
        if data then
            host:print("Loaded from cache")
            return host:json_encode(data)
        end
    end

    -- ... fetch fresh data ...

    -- Save to cache
    host:write_file("{cache_file}", host:json_encode(fresh_data))
""",
    },
    "iterate_results": {
        "label": "Iterate Over Results",
        "description": "Loop through a table of results and format output",
        "fields": [],
        "template": """
    local output = {}
    for i, item in ipairs(results) do
        output[#output + 1] = string.format(
            "%d. %s - %s",
            i,
            tostring(item.name or "N/A"),
            tostring(item.value or "N/A")
        )
    end
    return table.concat(output, "\\n")
""",
    },
    "hash_data": {
        "label": "Hash Data",
        "description": "Hash input text with a chosen algorithm",
        "fields": [
            {"key": "algorithm", "label": "Algorithm", "placeholder": "sha256"},
        ],
        "template": """
    local hash_result = host:hash(query, "{algorithm}")
    host:print("{algorithm} hash: " .. tostring(hash_result))
""",
    },
}

LUA_TIPS = [
    "host:print() outputs text to the UI - use it for progress updates",
    "Return nil, 'error message' to signal errors to the user",
    "host:http_get(url, timeout) returns body or nil, error",
    "host:json_decode(str) converts JSON to a Lua table",
    "host:get_config('key') reads user-configured plugin settings",
    "Use host:url_encode(query) before inserting into URLs",
    "host:cache_get/cache_set provide in-memory session cache",
    "Files via host:read_file/write_file are sandboxed to plugin dir",
    "host:sleep(seconds) max 60s - use sparingly",
    "host:hash(text, 'sha256') hashes text with any supported algorithm",
    "Use local variables to avoid polluting the sandbox environment",
    "table.concat(lines, '\\n') is the best way to build multiline output",
    "Lua arrays are 1-based: first element is t[1], not t[0]",
    "host:log(msg, 'warn') logs to app log + plugin output",
    "pcall(func) catches errors without crashing the plugin",
    "string.format('%s has %d items', name, count) for formatting",
    "Lua patterns: %d=digit, %a=letter, %w=alphanumeric, %s=space",
    "host:get_platform() returns 'Windows', 'Linux', or 'Darwin'",
]
