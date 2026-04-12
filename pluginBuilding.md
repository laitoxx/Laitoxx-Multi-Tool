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

## Русский

### Начало работы

Плагины Laitoxx пишутся на **Lua** и выполняются внутри безопасной песочницы. Каждый плагин — это один файл `.lua` в папке `lua_plugins/`. Приложение автоматически находит плагины при запуске.

**Быстрый старт:**
1. Откройте **Конструктор плагинов** в боковой панели
2. Заполните метаданные (имя, автор, описание, тип, целевая ОС)
3. Напишите код в встроенном редакторе с подсветкой синтаксиса
4. Сохраните — плагин сразу появится в категории **Плагины**

Или вручную: скопируйте `lua_plugins/_template.lua`, переименуйте, отредактируйте, перезапустите приложение.

> Файлы, начинающиеся с `_` (например `_template.lua`), игнорируются загрузчиком плагинов.

---

### Структура плагина

Каждый плагин должен возвращать таблицу с метаданными и хотя бы одной функцией-обработчиком:

```lua
local plugin = {
    id          = "my_plugin",        -- Уникальный ID (без пробелов, в нижнем регистре)
    name        = "Мой Плагин",       -- Отображаемое имя в UI
    description = "Что он делает.",    -- Показывается в подсказке
    author      = "Ваше Имя",
    version     = "1.0",
    type        = "search",           -- "search" | "processor" | "formatter" | "passive_scanner"

    -- Опционально: настраиваемые параметры
    config_schema = {
        { key = "api_key",     label = "API-ключ",       type = "string",  default = "" },
        { key = "max_results", label = "Макс. результатов", type = "number",  default = 10 },
        { key = "verbose",     label = "Подробный режим",  type = "boolean", default = false },
    },
}

function plugin.search(query, options)
    -- Ваша логика здесь
    return "строка результата"
end

return plugin  -- ВАЖНО: всегда возвращайте таблицу плагина
```

---

### Типы плагинов

| Тип | Основная функция | Применение |
|-----|-----------------|-----------|
| `search` | `plugin.search(query, options)` | Запросы к внешним API, базам данных, OSINT-источникам |
| `processor` | `plugin.process(data, options)` | Преобразование, обогащение или анализ данных |
| `formatter` | `plugin.format(data, options)` | Экспорт результатов в CSV, JSON, другие форматы |
| `passive_scanner` | `plugin.scan(target, options)` | Анализ входных данных без сетевых запросов |

> Совет: можно определить несколько функций. Например, плагин-процессор может также определить `plugin.search` как алиас.

---

### Справочник Host API

Все функции хоста вызываются через двоеточие: `host:метод(аргументы)`.

#### Вывод

| Функция | Описание |
|---------|----------|
| `host:print(...)` | Вывести текст в область результатов (отображается в UI) |
| `host:log(message, level)` | Записать в лог + вывод. Уровни: `"info"`, `"warn"`, `"error"`, `"debug"` |

#### HTTP-запросы

| Функция | Описание |
|---------|----------|
| `host:http_get(url, timeout, headers)` | GET-запрос. Возвращает `body` или `nil, ошибка` |
| `host:http_post(url, data, timeout, headers, content_type)` | POST-запрос. Возвращает `body` или `nil, ошибка` |

```lua
-- Пример GET
local body, err = host:http_get("https://api.example.com/data?q=" .. host:url_encode(query), 15)
if not body then
    return nil, "Запрос не удался: " .. (err or "неизвестная ошибка")
end

-- Пример POST с JSON
local payload = host:json_encode({ query = query, limit = 10 })
local body, err = host:http_post("https://api.example.com/search", payload, 15)
```

#### JSON

| Функция | Описание |
|---------|----------|
| `host:json_decode(string)` | Разобрать JSON-строку в таблицу Lua. Возвращает `table` или `nil, ошибка` |
| `host:json_encode(table)` | Конвертировать таблицу Lua в JSON-строку. Возвращает `string` или `nil, ошибка` |

```lua
local data, err = host:json_decode(body)
if not data then
    return nil, "Ошибка парсинга JSON: " .. (err or "неизвестно")
end

host:print("Имя: " .. tostring(data.name))
host:print("Количество: " .. tostring(data.results))
```

#### Файловая система (в песочнице)

Все файловые операции ограничены директорией плагина. Обход пути заблокирован.

| Функция | Описание |
|---------|----------|
| `host:read_file(path)` | Прочитать содержимое файла. Возвращает `string` или `nil, ошибка` |
| `host:write_file(path, content)` | Записать содержимое в файл. Возвращает `true` или `nil, ошибка` |
| `host:file_exists(path)` | Проверить существование файла. Возвращает `boolean` |

```lua
-- Сохранить результаты в файл внутри директории плагина
host:write_file("last_results.json", host:json_encode(results))

-- Прочитать кэшированные данные
local cached = host:read_file("cache.json")
if cached then
    local data = host:json_decode(cached)
end
```

#### Конфигурация

| Функция | Описание |
|---------|----------|
| `host:get_config(key)` | Получить значение настройки, установленной пользователем |
| `host:get_all_config()` | Получить все значения настроек как таблицу |

```lua
local api_key = host:get_config("api_key")
if not api_key or api_key == "" then
    return nil, "Установите API-ключ в настройках плагина (ПКМ по плагину)."
end
```

#### Утилиты

| Функция | Описание |
|---------|----------|
| `host:hash(text, algorithm)` | Хеширование текста. Алгоритмы: `"md5"`, `"sha1"`, `"sha256"`, `"sha512"` и др. |
| `host:base64_encode(text)` | Base64 кодирование |
| `host:base64_decode(text)` | Base64 декодирование. Возвращает `string` или `nil, ошибка` |
| `host:url_encode(text)` | URL-кодирование (percent encoding) |
| `host:url_decode(text)` | URL-декодирование |
| `host:sleep(seconds)` | Пауза выполнения (максимум 60 секунд) |
| `host:get_tool_version()` | Возвращает версию Laitoxx |
| `host:get_platform()` | Возвращает `"Windows"`, `"Linux"` или `"Darwin"` |

#### Кэш (в памяти, на время сессии)

| Функция | Описание |
|---------|----------|
| `host:cache_get(key)` | Получить кэшированное значение (теряется при перезапуске) |
| `host:cache_set(key, value)` | Установить кэшированное значение |
| `host:cache_clear()` | Очистить все кэшированные значения |

#### Graph API (Графы)

Плагины могут строить интерактивные графы (диаграммы связей), которые открываются во встроенном Редакторе графов. Когда плагин вызывает `host:graph_save()`, пользователю предлагается открыть граф.

| Функция | Описание |
|---------|----------|
| `host:graph_create(name, direction)` | Создать новый граф. `direction`: `"TD"`, `"LR"`, `"RL"`, `"BT"`. Возвращает `graph_id` |
| `host:graph_add_node(gid, label, node_type, shape, style, description)` | Добавить ноду. Возвращает `node_id` или `nil, ошибка` |
| `host:graph_add_edge(gid, src_id, tgt_id, label, edge_type, line_type, style)` | Добавить связь. Возвращает `edge_id` или `nil, ошибка` |
| `host:graph_find_node(gid, label)` | Найти ноду по метке. Возвращает `node_id` или `nil` |
| `host:graph_get_nodes(gid)` | Получить все ноды как таблицу `{id, label, type}` |
| `host:graph_save(gid, filename)` | Сохранить граф в JSON-файл. Возвращает `filepath` или `nil, ошибка`. **Вызывает запрос «Открыть граф?»** |
| `host:graph_set_direction(gid, direction)` | Изменить направление графа |
| `host:graph_node_set_style(gid, node_id, style)` | Переопределить CSS-стиль ноды |
| `host:graph_node_set_shape(gid, node_id, shape)` | Переопределить форму ноды |
| `host:graph_get_node_types()` | Получить доступные типы нод и их стили по умолчанию |

**Типы нод:** `"Person"`, `"Email"`, `"Phone"`, `"Website"`, `"Company"`, `"IP"`, `"Address"`, `"Document"`, `"Custom"`

**Формы:** `"rect"`, `"round"`, `"circle"`, `"diamond"`, `"hexagon"`, `"flag"`, `"trapez"`

**Типы линий:** `"-->"` (стрелка), `"==>"` (толстая), `"-.->"` (пунктир), `"---"` (без стрелки), `"<-->"` (двойная)

**Стиль** — строка CSS, например: `"fill:#FFD700,stroke:#8B4513,stroke-width:2px,color:#000"`

```lua
-- Пример использования Graph API
local gid = host:graph_create("Моё расследование", "LR")

-- Добавляем ноды с кастомными стилями
local n1 = host:graph_add_node(gid, "Иванов И.И.", "Person", "round",
    "fill:#FFD700,stroke:#8B4513,stroke-width:2px,color:#000", "Основная цель")
local n2 = host:graph_add_node(gid, "ivanov@example.com", "Email", "rect",
    "fill:#ADD8E6,stroke:#1E90FF,stroke-width:2px,color:#000")
local n3 = host:graph_add_node(gid, "+7-999-123-4567", "Phone", "rect",
    "fill:#98FB98,stroke:#228B22,stroke-width:2px,color:#000")

-- Добавляем связи с подписями
host:graph_add_edge(gid, n1, n2, "личная почта", "Connected", "-->")
host:graph_add_edge(gid, n1, n3, "мобильный", "Connected", "-->")

-- Сохраняем — пользователю будет предложено открыть граф
host:graph_save(gid, "investigation.graph.json")
```

> **Совет:** Определите таблицу `graph_styles` в вашем плагине, чтобы хранить все определения цветов/форм в одном месте. См. плагин LeakOSINT для полного примера с автоопределением типов данных.

---

### Обработка ошибок

Используйте паттерн `nil, "сообщение об ошибке"` для сигнализации об ошибках:

```lua
function plugin.search(query, options)
    if not query or query == "" then
        return nil, "Запрос не может быть пустым."
    end

    local body, err = host:http_get(url, 10)
    if not body then
        return nil, "HTTP-запрос не удался: " .. (err or "неизвестная ошибка")
    end

    -- Для безопасного выполнения рискованного кода:
    local ok, result = pcall(function()
        -- код, который может упасть
        return some_operation()
    end)
    if not ok then
        host:log("Внутренняя ошибка: " .. tostring(result), "error")
        return nil, "Что-то пошло не так."
    end

    return result
end
```

---

### Возвращаемые значения

Функция-обработчик может возвращать:

| Тип возврата | Что происходит |
|-------------|---------------|
| `string` | Отображается напрямую в области вывода |
| `table` | Автоматически конвертируется в форматированный JSON |
| `nil` | Ничего не отображается (используйте `host:print()` для вывода) |
| `nil, "ошибка"` | Сообщение об ошибке показывается пользователю |

---

### Схема конфигурации

Определите `config_schema` в таблице плагина, чтобы пользователи могли настраивать параметры через UI (ПКМ → Настройки плагина):

```lua
config_schema = {
    { key = "api_key",     label = "API-ключ",              type = "string",  default = "" },
    { key = "timeout",     label = "Таймаут (сек)",          type = "number",  default = 15 },
    { key = "show_raw",    label = "Показывать сырые данные", type = "boolean", default = false },
}
```

Поддерживаемые типы: `"string"`, `"number"`, `"boolean"`.

Доступ к значениям через `host:get_config("имя_ключа")`.

---

### Плагины для конкретных ОС

Если плагин работает только на определённых операционных системах:

```lua
function plugin.search(query, options)
    local platform = host:get_platform()
    if platform ~= "Windows" then
        return nil, "Этот плагин работает только на Windows."
    end
    -- Логика для Windows
end
```

Конструктор плагинов может автоматически сгенерировать эту проверку при выборе целевой ОС.

---

### Правила песочницы

Плагины выполняются в ограниченном окружении. **Доступно**:

- `print`, `type`, `tostring`, `tonumber`
- `pairs`, `ipairs`, `next`, `select`, `unpack`
- `pcall`, `xpcall`, `error`, `assert`
- `rawget`, `rawset`, `rawequal`
- `setmetatable`, `getmetatable`
- `string.*`, `table.*`, `math.*`
- Все функции `host:*`

**НЕ доступно** (заблокировано для безопасности):

- Модули `io`, `os`, `debug`
- `loadfile`, `dofile`, `load` (кроме внутреннего использования)
- `require`
- Прямой доступ к файловой системе
- Прямой сетевой доступ (используйте `host:http_get/post`)

---

### Лучшие практики

1. **Всегда проверяйте входные данные** — проверяйте, что `query` не nil и не пустой
2. **Обрабатывайте ошибки HTTP** — всегда проверяйте второе возвращаемое значение
3. **Используйте `host:print()`** для обновлений прогресса при долгих операциях
4. **Держите плагины сфокусированными** — один плагин, одна задача
5. **Используйте `config_schema`** для API-ключей вместо хардкода
6. **Используйте `local`** для всех переменных, чтобы не засорять песочницу
7. **Возвращайте понятные ошибки** — объясните, что пошло не так и как исправить
8. **Используйте `host:cache_set/get`** чтобы избежать лишних API-вызовов в рамках сессии
9. **Учитывайте rate limits** — используйте `host:sleep()` между частыми API-запросами
10. **Проверяйте синтаксис** — нажмите «Проверить синтаксис» перед сохранением

---

### Полный пример: плагин поиска по API

```lua
local plugin = {
    id          = "shodan_search",
    name        = "Shodan Search",
    description = "Поиск хостов и сервисов в Shodan.",
    author      = "Community",
    version     = "1.0",
    type        = "search",

    config_schema = {
        { key = "api_key", label = "Shodan API Key", type = "string", default = "" },
    },
}

function plugin.search(query, options)
    if not query or query == "" then
        return nil, "Введите IP-адрес или поисковый запрос."
    end

    local api_key = host:get_config("api_key")
    if not api_key or api_key == "" then
        return nil, "Нужен API-ключ Shodan. ПКМ по плагину → Настройки плагина."
    end

    host:print("Поиск в Shodan: " .. query)

    local url = "https://api.shodan.io/shodan/host/" .. host:url_encode(query)
        .. "?key=" .. host:url_encode(api_key)

    local body, err = host:http_get(url, 15)
    if not body then
        return nil, "Запрос к Shodan не удался: " .. (err or "неизвестная ошибка")
    end

    local data, err = host:json_decode(body)
    if not data then
        return nil, "Ошибка парсинга ответа: " .. (err or "неизвестно")
    end

    if data.error then
        return nil, "Ошибка Shodan: " .. tostring(data.error)
    end

    local lines = {
        "=== Результаты Shodan ===",
        "",
        "IP:       " .. tostring(data.ip_str or query),
        "Орг:      " .. tostring(data.org or "N/A"),
        "ОС:       " .. tostring(data.os or "N/A"),
        "Порты:    " .. table.concat(data.ports or {}, ", "),
        "Страна:   " .. tostring(data.country_name or "N/A"),
        "Город:    " .. tostring(data.city or "N/A"),
        "",
    }

    if data.data then
        lines[#lines + 1] = "Сервисы:"
        for i, svc in ipairs(data.data) do
            lines[#lines + 1] = string.format(
                "  %d/%-5s %s",
                svc.port or 0,
                tostring(svc.transport or "tcp"),
                tostring(svc.product or svc.module or "unknown")
            )
            if i >= 20 then
                lines[#lines + 1] = "  ... (обрезано)"
                break
            end
        end
    end

    lines[#lines + 1] = ""
    lines[#lines + 1] = "========================="
    return table.concat(lines, "\n")
end

return plugin
```

---

### Сниппеты в конструкторе

Конструктор плагинов предлагает готовые блоки кода через кнопку **«Вставить сниппет»**:

| Сниппет | Описание |
|---------|----------|
| HTTP GET Request | GET-запрос с обработкой ошибок |
| HTTP POST Request | POST-запрос с JSON-телом |
| Parse JSON Response | Парсинг JSON-ответа |
| GET + Parse JSON (Full) | Полный цикл: запрос → парсинг → обработка |
| Check Config Value | Проверка API-ключа из настроек |
| Format Output Lines | Построение многострочного вывода |
| Error Handling (pcall) | Безопасное выполнение через pcall |
| File-based Cache | Файловое кэширование |
| Iterate Over Results | Цикл по таблице результатов |
| Hash Data | Хеширование данных |

Каждый сниппет имеет настраиваемые поля и предпросмотр кода перед вставкой.
