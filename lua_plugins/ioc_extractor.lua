-- ============================================================================
-- IOC Extractor Plugin for Laitoxx
-- ============================================================================
-- Extracts Indicators of Compromise (IOCs) from text input:
-- IP addresses, email addresses, URLs, MD5/SHA hashes, domains.
-- Demonstrates: processor plugin type, string pattern matching.
-- ============================================================================

local plugin = {
    id          = "ioc_extractor",
    name        = "IOC Extractor (Lua)",
    description = "Extract indicators of compromise (IPs, emails, URLs, hashes, domains) from text.",
    author      = "Laitoxx Community",
    version     = "1.0",
    type        = "processor",

    config_schema = {
        { key = "deduplicate", label = "Remove duplicates", type = "boolean", default = true },
    },
}

--- Helper: find all matches of a pattern in text
local function find_all(text, pattern)
    local results = {}
    for match in text:gmatch(pattern) do
        results[#results + 1] = match
    end
    return results
end

--- Helper: deduplicate a list
local function dedupe(list)
    local seen = {}
    local result = {}
    for _, v in ipairs(list) do
        if not seen[v] then
            seen[v] = true
            result[#result + 1] = v
        end
    end
    return result
end

function plugin.search(query, options)
    if not query or query == "" then
        return nil, "Please paste text containing potential IOCs."
    end

    host:print("Extracting IOCs from input text...")

    local should_dedupe = host:get_config("deduplicate")
    if should_dedupe == nil then should_dedupe = true end

    -- Extract IOCs
    local ipv4s    = find_all(query, "%d+%.%d+%.%d+%.%d+")
    local emails   = find_all(query, "[%w%.%-_]+@[%w%.%-]+%.%w+")
    local urls     = find_all(query, "https?://[%w%.%-_/%%?&=#+:~@!$',;]+")
    local md5s     = find_all(query, "%f[%x]%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%f[^%x]")
    local sha256s  = find_all(query, "%f[%x]%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%f[^%x]")

    if should_dedupe then
        ipv4s   = dedupe(ipv4s)
        emails  = dedupe(emails)
        urls    = dedupe(urls)
        md5s    = dedupe(md5s)
        sha256s = dedupe(sha256s)
    end

    -- Format output
    local lines = { "=== IOC Extraction Results ===" , "" }

    local function section(title, items)
        lines[#lines + 1] = title .. " (" .. #items .. " found):"
        if #items == 0 then
            lines[#lines + 1] = "  (none)"
        else
            for _, item in ipairs(items) do
                lines[#lines + 1] = "  - " .. item
            end
        end
        lines[#lines + 1] = ""
    end

    section("IPv4 Addresses", ipv4s)
    section("Email Addresses", emails)
    section("URLs", urls)
    section("MD5 Hashes", md5s)
    section("SHA-256 Hashes", sha256s)

    local total = #ipv4s + #emails + #urls + #md5s + #sha256s
    lines[#lines + 1] = "Total IOCs found: " .. total
    lines[#lines + 1] = "=============================="

    return table.concat(lines, "\n")
end

-- Also works as processor (same logic)
plugin.process = plugin.search

return plugin
