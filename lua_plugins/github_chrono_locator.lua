local plugin = {
    id          = "github_chronolocation",
    name        = "GitHub Recursive OSINT & Chrono-Locator",
    description = "Вычисляет часовой пояс, находит скрытые email-адреса, внешние контрибьюты, соавторов и скрытые аккаунты (алиасы) через глубокий рекурсивный поиск.",
    author      = "Telegram @math_solvers (Deep OSINT Update)",
    version     = "3.0",
    type        = "search",

    config_schema = {
        { key = "gh_token", label = "GitHub Token (рекомендуется для поиска)", type = "string", default = "" },
        { key = "pages",    label = "Глубина анализа (стр. репозиториев)", type = "number", default = 2 },
    },
}

-- Вспомогательная функция для генерации sparkline
local function generate_sparkline(data)
    local ticks = { " ", "▂", "▃", "▄", "▅", "▆", "▇", "█" }
    local max_val = 0
    for i = 0, 23 do
        if data[i] > max_val then max_val = data[i] end
    end

    local sparkline = ""
    for i = 0, 23 do
        if max_val == 0 then
            sparkline = sparkline .. ticks[1]
        else
            local idx = math.ceil((data[i] / max_val) * #ticks)
            if idx == 0 then idx = 1 end
            sparkline = sparkline .. ticks[idx]
        end
    end
    return sparkline
end

-- Генерация заголовков для API
local function get_headers(token, is_search)
    local h = {}
    if token and token ~= "" then
        h["Authorization"] = "Bearer " .. token
    end
    if is_search then
        h["Accept"] = "application/vnd.github.cloak-preview+json"
    end
    
    local has_keys = false
    for k, v in pairs(h) do has_keys = true; break end
    return has_keys and h or nil
end

local function safe_http_get(url, timeout, headers)
    local is_search = url:match("/search/")
    while true do
        local body, err = host:http_get(url, timeout, headers)
        
        if body and body:match('"message":%s*"API rate limit exceeded') then
            host:log("Rate limit exceeded: " .. url, "warn")
            host:print("⚠️ Превышен лимит GitHub API. Ожидание сброса лимита (проверка каждую минуту)...")
            
            while true do
                local rl_body = host:http_get("https://api.github.com/rate_limit", timeout, headers)
                if rl_body then
                    local rl_data = host:json_decode(rl_body)
                    if rl_data and rl_data.resources then
                        local limit_obj = is_search and rl_data.resources.search or rl_data.resources.core
                        if limit_obj and limit_obj.remaining > 0 then
                            host:print("✅ Лимит API успешно сброшен! Продолжаем работу...")
                            break
                        end
                    end
                end
                host:sleep(60)
            end
        elseif body and body:match('"message":%s*"You have exceeded a secondary rate limit') then
            host:print("⚠️ Сработал вторичный лимит (Secondary Rate Limit). Ожидаем 60 секунд...")
            host:sleep(60)
        elseif err and err:match("429") then
            host:print("⚠️ Ошибка 429 (Слишком много запросов). Ожидаем 60 секунд...")
            host:sleep(60)
        else
            return body, err
        end
    end
end

local function extract_from_patch(patch_body, unique_emails, found_emails, co_authors)
    if not patch_body then return end
    
    local email = patch_body:match("From:%s*[^\n<]*<([^>\n]+)>")
    if email and not email:match("noreply%.github%.com$") and not unique_emails[email] then
        unique_emails[email] = true
        table.insert(found_emails, email)
        host:print("   📧 Найден новый email: " .. email)
    end
    
    for co_author in patch_body:gmatch("Co%-authored%-by:%s*[^\n<]*<([^>\n]+)>") do
        if not co_authors[co_author] and not co_author:match("noreply%.github%.com$") then
            co_authors[co_author] = true
            host:print("   🤝 Найден соавтор (Co-author): " .. co_author)
        end
    end
end

function plugin.search(query, options)
    if not query or query == "" then
        return nil, "Введите username или ссылку на профиль GitHub (например: torvalds или https://github.com/torvalds)."
    end

    local extracted_username = query:gsub("/+$", "")
    local gh_match = extracted_username:match("github%.com/([^/]+)")
    
    if gh_match then
        extracted_username = gh_match
    else
        local http_match = extracted_username:match("^https?://([^/]+)")
        if http_match then
            extracted_username = http_match
        end
    end

    local username = host:url_encode(extracted_username)
    local token = host:get_config("gh_token")
    local pages = tonumber(host:get_config("pages")) or 2

    host:print("🔍 Запуск расширенного OSINT-анализа для: " .. extracted_username)
    host:print("==============================================================")
    host:print("⏳ ЭТАП 1: Выкачиваем паттерны активности для хронолокации...")

    local activity_by_hour = {}
    for i = 0, 23 do activity_by_hour[i] = 0 end

    local repos_touched = {}
    local total_events = 0

    for page = 1, pages do
        local url = string.format("https://api.github.com/users/%s/events/public?per_page=100&page=%d", username, page)
        local body, err = safe_http_get(url, 50, get_headers(token, false))
        
        if not body then
            return nil, "Ошибка доступа к GitHub API: " .. (err or "неизвестно")
        end

        local data, err_json = host:json_decode(body)
        if not data then
            return nil, "Ошибка парсинга ответа от GitHub: " .. (err_json or "неизвестно")
        end

        if data.message and data.message == "Not Found" then
            return nil, "Пользователь не найден."
        end

        if #data == 0 then break end

        for _, event in ipairs(data) do
            if event.created_at then
                local y, m, d, h, min, s = event.created_at:match("^(%d+)%-(%d+)%-(%d+)T(%d+):(%d+):(%d+)Z$")
                if h then
                    local hour_utc = tonumber(h)
                    activity_by_hour[hour_utc] = activity_by_hour[hour_utc] + 1
                    total_events = total_events + 1

                    if event.repo and event.repo.name then
                        repos_touched[event.repo.name] = (repos_touched[event.repo.name] or 0) + 1
                    end
                end
            end
        end
    end

    local sleep_start_utc = 0
    local inferred_timezone = "Неизвестно"
    local sorted_repos = {}

    if total_events > 0 then
        local min_commits = 999999
        for i = 0, 23 do
            local current_commits = 0
            for j = 0, 7 do
                local hour_index = (i + j) % 24
                current_commits = current_commits + activity_by_hour[hour_index]
            end
            if current_commits < min_commits then
                min_commits = current_commits
                sleep_start_utc = i
            end
        end

        local estimated_offset = (23 - sleep_start_utc)
        if estimated_offset > 12 then estimated_offset = estimated_offset - 24 end
        if estimated_offset < -12 then estimated_offset = estimated_offset + 24 end

        local tz_sign = estimated_offset >= 0 and "+" or ""
        inferred_timezone = string.format("UTC%s%d", tz_sign, estimated_offset)

        for repo, count in pairs(repos_touched) do
            table.insert(sorted_repos, {name = repo, count = count})
        end
        table.sort(sorted_repos, function(a, b) return a.count > b.count end)
    end

    host:print("==============================================================")
    host:print("⏳ ЭТАП 2: Сбор собственных публичных репозиториев...")

    local repos = {}
    local r_page = 1
    while true do
        local url = string.format("https://api.github.com/users/%s/repos?per_page=100&page=%d", username, r_page)
        local body, err = safe_http_get(url, 30, get_headers(token, false))
        if not body then break end
        
        local data = host:json_decode(body)
        if not data or data.message or #data == 0 then break end
        
        for _, repo in ipairs(data) do
            table.insert(repos, repo.name)
        end
        r_page = r_page + 1
    end

    host:print("📂 Найдено публичных репозиториев профиля: " .. #repos)
    host:print("==============================================================")
    host:print("⏳ ЭТАП 3: Анализ коммитов в собственных репозиториях...")

    local unique_emails = {}
    local found_emails = {}
    local co_authors = {}
    local total_commits_checked = 0

    for idx, repo_name in ipairs(repos) do
        host:print(string.format("  [%d/%d] Проверка коммитов в %s...", idx, #repos, repo_name))
        local c_page = 1
        while true do
            local url = string.format("https://api.github.com/repos/%s/%s/commits?author=%s&per_page=100&page=%d", username, host:url_encode(repo_name), username, c_page)
            local body, err = safe_http_get(url, 30, get_headers(token, false))
            if not body then break end
            
            local data = host:json_decode(body)
            if not data or data.message or #data == 0 then break end
            
            for _, commit in ipairs(data) do
                if commit.sha then
                    total_commits_checked = total_commits_checked + 1
                    local patch_url = string.format("https://github.com/%s/%s/commit/%s.patch", username, host:url_encode(repo_name), commit.sha)
                    local patch_body, patch_err = safe_http_get(patch_url, 30, nil)
                    extract_from_patch(patch_body, unique_emails, found_emails, co_authors)
                end
            end
            c_page = c_page + 1
        end
    end

    host:print("==============================================================")
    host:print("⏳ ЭТАП 4: Поиск следов в чужих (внешних) репозиториях...")
    
    local external_repos = {}
    local search_url_ext = string.format("https://api.github.com/search/commits?q=author:%s+-user:%s+is:public&per_page=100", username, username)
    local s_body_ext = safe_http_get(search_url_ext, 30, get_headers(token, true))
    
    if s_body_ext then
        local s_data_ext = host:json_decode(s_body_ext)
        if s_data_ext and s_data_ext.items then
            host:print("🌐 Найдено внешних коммитов: " .. #s_data_ext.items)
            for _, item in ipairs(s_data_ext.items) do
                if item.repository and item.repository.full_name then
                    external_repos[item.repository.full_name] = true
                end
                if item.sha and item.repository and item.repository.full_name then
                    total_commits_checked = total_commits_checked + 1
                    local patch_url = string.format("https://github.com/%s/commit/%s.patch", item.repository.full_name, item.sha)
                    local patch_body = safe_http_get(patch_url, 30, nil)
                    extract_from_patch(patch_body, unique_emails, found_emails, co_authors)
                end
            end
        end
    end

    host:print("==============================================================")
    host:print("⏳ ЭТАП 5: Рекурсивный поиск твинков и алиасов по Email...")
    
    local aliases = {}
    for _, email in ipairs(found_emails) do
        host:print("  -> Пробиваем Email: " .. email)
        local e_url = string.format("https://api.github.com/search/commits?q=author-email:%s+is:public&per_page=30", host:url_encode(email))
        local e_body = safe_http_get(e_url, 30, get_headers(token, true))
        if e_body then
            local e_data = host:json_decode(e_body)
            if e_data and e_data.items then
                for _, item in ipairs(e_data.items) do
                    if item.author and item.author.login and item.author.login:lower() ~= extracted_username:lower() then
                        local alias = item.author.login
                        if not aliases[alias] then
                            aliases[alias] = true
                            host:print("   👤 Найден связанный аккаунт (Алиас): " .. alias)
                        end
                    end
                    if item.repository and item.repository.full_name then
                        external_repos[item.repository.full_name] = true
                    end
                end
            end
        end
    end

    local lines = {
        "╔════════════════════════════════════════════════════════════╗",
        "║ 🕵️‍♂️ ПРОФИЛЬ GITHUB RECON: " .. string.format("%-33s", extracted_username) .. " ║",
        "╚════════════════════════════════════════════════════════════╝",
        "",
        "📊 Всего проанализировано коммитов: " .. tostring(total_commits_checked),
        "",
        "=== ⏱️ ХРОНОЛОКАЦИЯ (Анализ часового пояса) ==="
    }

    if total_events > 0 then
        table.insert(lines, "Глубокая фаза неактивности (UTC): " .. string.format("%02d:00 - %02d:00", sleep_start_utc, (sleep_start_utc + 8) % 24))
        table.insert(lines, "📍 ВЕРОЯТНЫЙ ЧАСОВОЙ ПОЯС:        " .. inferred_timezone)
        table.insert(lines, "")
        table.insert(lines, "=== 📈 СУТОЧНЫЙ ГРАФИК АКТИВНОСТИ (по UTC) ===")
        table.insert(lines, "00h 04h 08h 12h 16h 20h 23h")
        table.insert(lines, " |   |   |   |   |   |   |")
        table.insert(lines, " " .. generate_sparkline(activity_by_hour))
    else
        table.insert(lines, "⚠️ Недостаточно данных о недавних событиях для хронолокации.")
    end

    table.insert(lines, "")
    table.insert(lines, "=== 📧 ИЗВЛЕЧЕННЫЕ EMAIL АДРЕСА ===")
    if #found_emails > 0 then
        for i, email in ipairs(found_emails) do
            table.insert(lines, " -> " .. email)
        end
    else
        table.insert(lines, "❌ Приватные email-адреса не найдены (или скрыты настройками noreply).")
    end

    local aliases_list = {}
    for alias, _ in pairs(aliases) do table.insert(aliases_list, alias) end
    if #aliases_list > 0 then
        table.insert(lines, "")
        table.insert(lines, "=== 👤 СВЯЗАННЫЕ АККАУНТЫ (Алиасы/Твинки) ===")
        for _, alias in ipairs(aliases_list) do
            table.insert(lines, " -> " .. alias)
        end
    end

    local co_authors_list = {}
    for ca, _ in pairs(co_authors) do table.insert(co_authors_list, ca) end
    if #co_authors_list > 0 then
        table.insert(lines, "")
        table.insert(lines, "=== 🤝 СОАВТОРЫ (Связи) ===")
        for _, ca in ipairs(co_authors_list) do
            table.insert(lines, " -> " .. ca)
        end
    end

    local ext_repos_list = {}
    for repo, _ in pairs(external_repos) do table.insert(ext_repos_list, repo) end
    if #ext_repos_list > 0 then
        table.insert(lines, "")
        table.insert(lines, "=== 🌐 ВНЕШНИЕ РЕПОЗИТОРИИ (Следы контрибьютов) ===")
        for _, repo in ipairs(ext_repos_list) do
            table.insert(lines, " -> " .. repo)
        end
    end

    return table.concat(lines, "\n")
end

return plugin
