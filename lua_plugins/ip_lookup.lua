-- ============================================================================
-- IP Lookup Plugin for Laitoxx
-- ============================================================================
-- Example plugin that looks up IP address information using a free API.
-- Demonstrates: HTTP requests, JSON parsing, output formatting, error handling.
-- ============================================================================

local plugin = {
    id          = "ip_lookup",
    name        = "IP Lookup (Lua)",
    description = "Look up geolocation and network info for an IP address using ip-api.com (free, no key required).",
    author      = "Laitoxx Community",
    version     = "1.0",
    type        = "search",

    config_schema = {
        { key = "language", label = "Response Language (en/ru/de/fr/ja/zh-CN)", type = "string", default = "en" },
    },
}

function plugin.search(query, options)
    if not query or query == "" then
        return nil, "Please enter an IP address or domain name."
    end

    local ip = query:match("^%s*(.-)%s*$")  -- trim whitespace
    host:print("Looking up: " .. ip)

    local lang = host:get_config("language") or "en"
    local url = "http://ip-api.com/json/" .. host:url_encode(ip)
        .. "?fields=status,message,country,regionName,city,zip,lat,lon,timezone,isp,org,as,query"
        .. "&lang=" .. host:url_encode(lang)

    local body, err = host:http_get(url, 10)
    if not body then
        return nil, "HTTP request failed: " .. (err or "unknown error")
    end

    local data, err = host:json_decode(body)
    if not data then
        return nil, "Failed to parse JSON: " .. (err or "unknown error")
    end

    if data.status == "fail" then
        return nil, "API error: " .. (data.message or "unknown")
    end

    -- Format output
    local lines = {
        "=== IP Lookup Results ===",
        "",
        "IP:        " .. (data.query or ip),
        "Country:   " .. (data.country or "N/A"),
        "Region:    " .. (data.regionName or "N/A"),
        "City:      " .. (data.city or "N/A"),
        "ZIP:       " .. (data.zip or "N/A"),
        "Lat/Lon:   " .. tostring(data.lat or "?") .. ", " .. tostring(data.lon or "?"),
        "Timezone:  " .. (data.timezone or "N/A"),
        "ISP:       " .. (data.isp or "N/A"),
        "Org:       " .. (data.org or "N/A"),
        "AS:        " .. tostring(data["as"] or "N/A"),
        "",
        "=========================",
    }

    return table.concat(lines, "\n")
end

return plugin
