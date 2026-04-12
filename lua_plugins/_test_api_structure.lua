-- Test plugin for inspecting the LeakOSINT API response structure
-- File starts with _ so it is not loaded automatically

local plugin = {
    id          = "leakosint_test",
    name        = "LeakOSINT Structure Test",
    description = "Тест структуры ответа API",
    author      = "debug",
    version     = "0.1",
    type        = "search",
    config_schema = {
        { key = "token", label = "API Токен", type = "string", default = "" },
    },
}

-- Recursively print table structure with value types
local function dump_structure(tbl, prefix, depth, max_depth)
    prefix = prefix or ""
    depth = depth or 0
    max_depth = max_depth or 3

    if depth > max_depth then
        host:print(prefix .. " ... (max depth)")
        return
    end

    if type(tbl) ~= "table" then
        host:print(prefix .. " = " .. tostring(tbl) .. "  [" .. type(tbl) .. "]")
        return
    end

    local count = 0
    for k, v in pairs(tbl) do
        count = count + 1
        local key_str = tostring(k)
        if type(v) == "table" then
            host:print(prefix .. key_str .. " = {table}")
            if count <= 3 or depth < 1 then
                dump_structure(v, prefix .. "  ", depth + 1, max_depth)
            else
                host:print(prefix .. "  ... (skipped, showing first 3)")
            end
        else
            local val = tostring(v)
            if #val > 80 then val = string.sub(val, 1, 77) .. "..." end
            host:print(prefix .. key_str .. " = " .. val .. "  [" .. type(v) .. "]")
        end
        if count >= 10 and depth >= 1 then
            host:print(prefix .. "... (" .. count .. "+ keys)")
            break
        end
    end
end

function plugin.search(query, options)
    if not query or query == "" then
        return nil, "Введите запрос"
    end

    local token = host:get_config("token")
    if not token or token == "" then
        return nil, "Нет токена"
    end

    local payload = host:json_encode({
        token = token,
        request = query,
        limit = 10,
        lang = "ru",
        type = "json"
    })

    host:print("=== Запрос: " .. query .. " ===")
    host:print("")

    local body, err = host:http_post("https://leakosintapi.com/", payload, 30, nil, "application/json")
    if not body then
        return nil, "Ошибка: " .. tostring(err)
    end

    local data, err = host:json_decode(body)
    if not data then
        return nil, "JSON ошибка: " .. tostring(err)
    end

    host:print("=== СТРУКТУРА ВЕРХНЕГО УРОВНЯ ===")
    host:print("")

    for k, v in pairs(data) do
        local key_str = tostring(k)
        if type(v) == "table" then
            host:print("KEY: " .. key_str .. "  [table]")
            -- Show first 2 sub-entries in detail
            local sub_count = 0
            for sk, sv in pairs(v) do
                sub_count = sub_count + 1
                local sk_str = tostring(sk)
                if type(sv) == "table" then
                    host:print("  " .. sk_str .. " = {table}")
                    for ssk, ssv in pairs(sv) do
                        local ssk_str = tostring(ssk)
                        if type(ssv) == "table" then
                            host:print("    " .. ssk_str .. " = {table, keys:}")
                            local inner_count = 0
                            for ik, iv in pairs(ssv) do
                                inner_count = inner_count + 1
                                local val = tostring(iv)
                                if #val > 60 then val = string.sub(val, 1, 57) .. "..." end
                                host:print("      " .. tostring(ik) .. " = " .. val .. "  [" .. type(iv) .. "]")
                                if inner_count >= 8 then
                                    host:print("      ... (more keys)")
                                    break
                                end
                            end
                        else
                            local val = tostring(ssv)
                            if #val > 60 then val = string.sub(val, 1, 57) .. "..." end
                            host:print("    " .. ssk_str .. " = " .. val .. "  [" .. type(ssv) .. "]")
                        end
                    end
                else
                    local val = tostring(sv)
                    if #val > 60 then val = string.sub(val, 1, 57) .. "..." end
                    host:print("  " .. sk_str .. " = " .. val)
                end
                if sub_count >= 3 then
                    host:print("  ... (more entries)")
                    break
                end
            end
        else
            host:print("KEY: " .. key_str .. " = " .. tostring(v) .. "  [" .. type(v) .. "]")
        end
        host:print("")
    end

    host:print("=== RAW JSON (первые 2000 символов) ===")
    local raw = host:json_encode(data)
    if raw and #raw > 2000 then
        raw = string.sub(raw, 1, 2000) .. "..."
    end
    host:print(raw or "nil")

    return nil
end

return plugin
