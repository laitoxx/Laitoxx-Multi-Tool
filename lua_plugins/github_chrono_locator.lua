local plugin = {
    id          = "github_chronolocation",
    name        = "GitHub Chrono-Locator & Email Extractor",
    description = "Вычисляет реальный часовой пояс пользователя и извлекает все публичные email-адреса из патчей коммитов во всех репозиториях.",
    author      = "Telegram @math_solvers (Updated)",
    version     = "2.0",
    type        = "search",

    config_schema = {
        { key = "gh_token", label = "GitHub Token (настоятельно рекомендуется)", type = "string", default = "" },
        { key = "pages",    label = "Глубина анализа активности (стр)", type = "number", default = 2 },
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

-- Безопасный HTTP GET запрос с обработкой Rate Limits
local function safe_http_get(url, timeout, headers)
    while true do
        local body, err = host:http_get(url, timeout, headers)
        
        if body and body:match('"message":%s*"API rate limit exceeded') then
            host:log("Rate limit exceeded: " .. url, "warn")
            host:print("⚠️ Превышен лимит GitHub API. Ожидание сброса лимита (проверка каждую минуту)...")
            
            while true do
                local rl_body = host:http_get("https://api.github.com/rate_limit", timeout, headers)
                if rl_body then
                    local rl_data = host:json_decode(rl_body)
                    if rl_data and rl_data.resources and rl_data.resources.core and rl_data.resources.core.remaining > 0 then
                        host:print("✅ Лимит API успешно сброшен! Продолжаем работу...")
                        break
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

    local headers = nil
    if token and token ~= "" then
        headers = { ["Authorization"] = "Bearer " .. token }
    end

    host:print("🔍 Запуск расширенного анализа для: " .. query)
    host:print("==============================================================")
    host:print("⏳ ЭТАП 1: Выкачиваем паттерны активности для хронолокации...")

    local activity_by_hour = {}
    for i = 0, 23 do activity_by_hour[i] = 0 end

    local repos_touched = {}
    local total_events = 0

    -- Собираем данные об активности
    for page = 1, pages do
        local url = string.format("https://api.github.com/users/%s/events/public?per_page=100&page=%d", username, page)
        local body, err = safe_http_get(url, 50, headers)
        
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
    host:print("⏳ ЭТАП 2: Сбор публичных репозиториев...")

    local repos = {}
    local r_page = 1
    while true do
        local url = string.format("https://api.github.com/users/%s/repos?per_page=100&page=%d", username, r_page)
        local body, err = safe_http_get(url, 30, headers)
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
    host:print("⏳ ЭТАП 3: Анализ всех коммитов и извлечение email-адресов...")

    local unique_emails = {}
    local found_emails = {}
    local total_commits_checked = 0

    for idx, repo_name in ipairs(repos) do
        host:print(string.format("  [%d/%d] Проверка коммитов в %s...", idx, #repos, repo_name))
        local c_page = 1
        while true do
            local url = string.format("https://api.github.com/repos/%s/%s/commits?author=%s&per_page=100&page=%d", username, host:url_encode(repo_name), username, c_page)
            local body, err = safe_http_get(url, 30, headers)
            if not body then break end
            
            local data = host:json_decode(body)
            if not data or data.message or #data == 0 then break end
            
            for _, commit in ipairs(data) do
                if commit.sha then
                    total_commits_checked = total_commits_checked + 1
                    
                    -- Загрузка .patch файла для коммита
                    local patch_url = string.format("https://github.com/%s/%s/commit/%s.patch", username, host:url_encode(repo_name), commit.sha)
                    local patch_body, patch_err = safe_http_get(patch_url, 30, nil) -- Токен не передаем к github.com, только к api.github.com
                    
                    if patch_body then
                        -- Ищем строку "From: Имя <email@domain>" строго на одной строке
                        local email = patch_body:match("From:%s*[^\n<]*<([^>\n]+)>")
                        if email and not email:match("noreply%.github%.com$") and not unique_emails[email] then
                            unique_emails[email] = true
                            table.insert(found_emails, email)
                            host:print("   📧 Найден новый email: " .. email)
                        end
                    end
                end
            end
            c_page = c_page + 1
        end
    end

    -- Формируем финальный отчет
    local lines = {
        "╔════════════════════════════════════════════════════════════╗",
        "║ 🕵️‍♂️ ПРОФИЛЬ АКТИВНОСТИ GITHUB: " .. string.format("%-28s", query) .. " ║",
        "╚════════════════════════════════════════════════════════════╝",
        "",
        "📊 Проанализировано событий (активность): " .. tostring(total_events),
        "📊 Проанализировано репозиториев: " .. tostring(#repos),
        "📊 Проанализировано коммитов: " .. tostring(total_commits_checked),
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
        table.insert(lines, "")
        table.insert(lines, "=== 📂 ТОП-5 АКТИВНЫХ РЕПОЗИТОРИЕВ ===")
        local max_repos = math.min(5, #sorted_repos)
        for i = 1, max_repos do
            table.insert(lines, string.format(" %d. %s (%d событий)", i, sorted_repos[i].name, sorted_repos[i].count))
        end
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

    return table.concat(lines, "\n")
end

return plugin
