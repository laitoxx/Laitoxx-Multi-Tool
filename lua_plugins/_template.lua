-- ============================================================================
-- Laitoxx Lua Plugin Template
-- ============================================================================
--
-- This is a template for creating Lua plugins for Laitoxx.
-- Copy this file, rename it, and modify to create your own plugin.
--
-- STRUCTURE:
--   1. Define a `plugin` table with metadata
--   2. Implement one or more handler functions (search, process, format)
--   3. Return the plugin table at the end
--
-- AVAILABLE HOST API (via `host`):
--
--   Output:
--     host:log(message, level)       -- Log message ("info", "warn", "error", "debug")
--     host:print(...)                -- Print to plugin output (shown in UI)
--
--   HTTP:
--     host:http_get(url, timeout, headers_table)   -- GET request, returns body or nil,err
--     host:http_post(url, data, timeout, headers)  -- POST request, returns body or nil,err
--
--   JSON:
--     host:json_decode(string)       -- Parse JSON string -> Lua table
--     host:json_encode(table)        -- Lua table -> JSON string
--
--   Files (sandboxed to plugin directory):
--     host:read_file(path)           -- Read file contents
--     host:write_file(path, content) -- Write file
--     host:file_exists(path)         -- Check if file exists
--
--   Config:
--     host:get_config(key)           -- Get a user-configured value
--     host:get_all_config()          -- Get all config values as table
--
--   Utilities:
--     host:hash(text, algorithm)     -- Hash text (md5, sha256, etc.)
--     host:base64_encode(text)       -- Base64 encode
--     host:base64_decode(text)       -- Base64 decode
--     host:url_encode(text)          -- URL-encode
--     host:url_decode(text)          -- URL-decode
--     host:sleep(seconds)            -- Sleep (max 60s)
--     host:get_tool_version()        -- Get Laitoxx version
--     host:get_platform()            -- Get OS name
--
--   Cache (in-memory, per session):
--     host:cache_get(key)            -- Get cached value
--     host:cache_set(key, value)     -- Set cached value
--     host:cache_clear()             -- Clear cache
--
-- ERROR HANDLING:
--   Return nil, "error message" from your functions to signal errors.
--   The host will display the error message to the user.
--
-- CONFIG SCHEMA:
--   Define `config_schema` in your plugin table to allow users to
--   configure your plugin via the UI. Each entry is a table with:
--     { key = "api_key", label = "API Key", type = "string", default = "" }
--   Supported types: "string", "number", "boolean"
--
-- ============================================================================

local plugin = {
    -- Required metadata
    id          = "template",                  -- Unique plugin ID (no spaces)
    name        = "Template Plugin",           -- Display name
    description = "A template for creating Lua plugins.",
    author      = "Your Name",
    version     = "1.0",

    -- Plugin type: "search", "processor", "formatter", "passive_scanner"
    type        = "search",

    -- Optional: define user-configurable settings
    -- These will generate a settings form in the UI
    config_schema = {
        { key = "api_key",    label = "API Key",     type = "string",  default = "" },
        { key = "max_results", label = "Max Results", type = "number",  default = 10 },
        { key = "verbose",    label = "Verbose Mode", type = "boolean", default = false },
    },
}

-- ============================================================================
-- Plugin Functions
-- ============================================================================

--- Search function (for type = "search")
--- @param query string   The user's search query
--- @param options table   Additional options
--- @return string|table|nil  Results to display, or nil + error message
function plugin.search(query, options)
    if not query or query == "" then
        return nil, "Query cannot be empty"
    end

    host:print("Searching for: " .. query)

    -- Example: use config values
    local api_key = host:get_config("api_key")
    if not api_key or api_key == "" then
        return nil, "API Key is not configured. Please set it in plugin settings."
    end

    -- Example: make an HTTP request
    -- local body, err = host:http_get("https://api.example.com/search?q=" .. host:url_encode(query))
    -- if not body then
    --     return nil, "HTTP request failed: " .. (err or "unknown error")
    -- end

    -- Example: parse JSON response
    -- local data, err = host:json_decode(body)
    -- if not data then
    --     return nil, "Failed to parse response: " .. (err or "unknown error")
    -- end

    -- Return results (string or table)
    return "Template plugin executed successfully for query: " .. query
end

--- Process function (for type = "processor")
--- @param data string    Input data to process
--- @param options table   Additional options
--- @return string|nil     Processed result, or nil + error message
function plugin.process(data, options)
    host:print("Processing data...")
    -- Add your processing logic here
    return data
end

--- Format function (for type = "formatter")
--- @param data string    Data to format
--- @param options table   Additional options
--- @return string|nil     Formatted result, or nil + error message
function plugin.format(data, options)
    host:print("Formatting data...")
    -- Add your formatting logic here
    return data
end

-- ============================================================================
-- IMPORTANT: Always return the plugin table!
-- ============================================================================
return plugin
