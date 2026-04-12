local plugin = {
    id          = "github_chronolocation",
    name        = "GitHub Chrono-Locator",
    description = "Продвинутый анализ профиля GitHub: вычисляет реальный часовой пояс, график сна и привычки разработчика на основе таймстампов коммитов.",
    author      = "Telegram @math_solvers",
    version     = "1.0",
    type        = "search",

    config_schema = {
        { key = "gh_token", label = "GitHub Token (опционально, от лимитов)", type = "string", default = "" },
        { key = "pages",    label = "Глубина анализа (страниц)", type = "number", default = 2 },
    },
}

-- Helper function to generate an ASCII sparkline chart
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

function plugin.search(query, options)
    if not query or query == "" then
        return nil, "Введите username пользователя GitHub (например: torvalds)."
    end

    local username = host:url_encode(query)
    local token = host:get_config("gh_token")
    local pages = tonumber(host:get_config("pages")) or 2

    local headers = nil
    if token and token ~= "" then
        headers = { ["Authorization"] = "Bearer " .. token }
    end

    host:print("🔍 Запуск хронолокации для: " .. query)
    host:print("⏳ Выкачиваем паттерны активности (это может занять пару секунд)...")

    local activity_by_hour = {}
    for i = 0, 23 do activity_by_hour[i] = 0 end

    local days_activity = { weekend = 0, weekday = 0 }
    local repos_touched = {}
    local total_events = 0

    -- Collect data across multiple API pages
    for page = 1, pages do
        local url = string.format("https://api.github.com/users/%s/events/public?per_page=100&page=%d", username, page)
        local body, err = host:http_get(url, 50, headers)
        
        if not body then
            return nil, "Ошибка доступа к GitHub API: " .. (err or "неизвестно")
        end

        local data, err_json = host:json_decode(body)
        if not data then
            return nil, "Ошибка парсинга ответа от GitHub: " .. (err_json or "неизвестно")
        end

        if data.message and data.message:match("rate limit") then
            return nil, "Превышен лимит запросов GitHub. Добавьте токен в настройки плагина."
        elseif data.message and data.message == "Not Found" then
            return nil, "Пользователь не найден."
        end

        if #data == 0 then break end -- No more events

        for _, event in ipairs(data) do
            -- Parse timestamp in the format "2023-10-01T15:30:00Z"
            if event.created_at then
                local y, m, d, h, min, s = event.created_at:match("^(%d+)%-(%d+)%-(%d+)T(%d+):(%d+):(%d+)Z$")
                if h then
                    local hour_utc = tonumber(h)
                    activity_by_hour[hour_utc] = activity_by_hour[hour_utc] + 1
                    total_events = total_events + 1

                    -- Track unique repositories
                    if event.repo and event.repo.name then
                        repos_touched[event.repo.name] = (repos_touched[event.repo.name] or 0) + 1
                    end
                end
            end
        end
        host:sleep(0.5) -- Small delay to avoid hammering the API
    end

    if total_events == 0 then
        return "⚠️ У пользователя нет недавней публичной активности для анализа."
    end

    -- CHRONOLOCATION ALGORITHM: Find the 8-hour sleep window (lowest activity)
    local min_commits = 999999
    local sleep_start_utc = 0

    for i = 0, 23 do
        local current_commits = 0
        for j = 0, 7 do -- 8-hour sleep window
            local hour_index = (i + j) % 24
            current_commits = current_commits + activity_by_hour[hour_index]
        end
        
        if current_commits < min_commits then
            min_commits = current_commits
            sleep_start_utc = i
        end
    end

    -- Assume the start of the sleep window is approximately 23:00 (11 PM) in the target's local time.
    -- Calculate UTC offset from that assumption.
    local estimated_offset = (23 - sleep_start_utc)
    if estimated_offset > 12 then estimated_offset = estimated_offset - 24 end
    if estimated_offset < -12 then estimated_offset = estimated_offset + 24 end

    local tz_sign = estimated_offset >= 0 and "+" or ""
    local inferred_timezone = string.format("UTC%s%d", tz_sign, estimated_offset)

    -- Sort repositories by interaction frequency
    local sorted_repos = {}
    for repo, count in pairs(repos_touched) do
        table.insert(sorted_repos, {name = repo, count = count})
    end
    table.sort(sorted_repos, function(a, b) return a.count > b.count end)

    -- Build the output report
    local lines = {
        "╔════════════════════════════════════════════════════════════╗",
        "║ 🕵️‍♂️ ПРОФИЛЬ АКТИВНОСТИ GITHUB: " .. string.format("%-28s", query) .. " ║",
        "╚════════════════════════════════════════════════════════════╝",
        "",
        "📊 Всего проанализировано событий: " .. tostring(total_events),
        "",
        "=== ⏱️ ХРОНОЛОКАЦИЯ (Анализ часового пояса) ===",
        "Глубокая фаза неактивности (UTC): " .. string.format("%02d:00 - %02d:00", sleep_start_utc, (sleep_start_utc + 8) % 24),
        "📍 ВЕРОЯТНЫЙ ЧАСОВОЙ ПОЯС:        " .. inferred_timezone,
        "",
        "=== 📈 СУТОЧНЫЙ ГРАФИК АКТИВНОСТИ (по UTC) ===",
        "00h 04h 08h 12h 16h 20h 23h",
        " |   |   |   |   |   |   |",
        " " .. generate_sparkline(activity_by_hour),
        "",
        "=== 📂 ТОП-5 АКТИВНЫХ РЕПОЗИТОРИЕВ ==="
    }

    local max_repos = math.min(5, #sorted_repos)
    for i = 1, max_repos do
        table.insert(lines, string.format(" %d. %s (%d событий)", i, sorted_repos[i].name, sorted_repos[i].count))
    end

    if #sorted_repos > 5 then
        table.insert(lines, " ... и еще " .. tostring(#sorted_repos - 5) .. " репозиториев.")
    end

    table.insert(lines, "")
    table.insert(lines, "==============================================================")
    table.insert(lines, "[!] Примечание: Часовой пояс вычислен на основе паттернов сна.")
    table.insert(lines, "    Если цель работает в ночную смену, данные могут быть сдвинуты.")

    return table.concat(lines, "\n")
end

return plugin