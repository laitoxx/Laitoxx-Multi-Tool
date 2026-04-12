local plugin = {
    id          = "leakosint_search",
    name        = "LeakOSINT API Search",
    description = "Поиск по базам утечек LeakOSINT с построением графа связей (email, телефон, авто, ФИО и др.)",
    author      = "Telegram @math_solvers",
    version     = "2.0",
    type        = "search",

    -- Configurable parameters (accessible via right-click -> Plugin Settings)
    config_schema = {
        { key = "token", label = "API Токен (команда /api в боте)", type = "string", default = "" },
        { key = "limit", label = "Лимит результатов (10 - 10000)", type = "number", default = 100 },
        { key = "lang",  label = "Язык результатов (ru/en)", type = "string", default = "ru" },
        { key = "type",  label = "Тип отчета (json/short/html)", type = "string", default = "json" },
        { key = "depth", label = "Глубина поиска (0 = без графа, 1 = доп. поиск по найденным данным)", type = "number", default = 0 },
        { key = "depth_max_queries", label = "Макс. доп. запросов (уровень 1)", type = "number", default = 10 },
        { key = "depth_name_only", label = "Глубина: искать по одному ФИО без даты (риск лишних запросов)", type = "boolean", default = false },
        { key = "debug_dump", label = "Debug: сохранять JSON ответы в файлы", type = "boolean", default = false },
        { key = "debug_dump_limit", label = "Debug: лимит дампов уровня 1", type = "number", default = 5 },
        { key = "max_records_per_db", label = "Граф: макс. записей на БД", type = "number", default = 30 },
        { key = "max_fields_per_record", label = "Граф: макс. полей на запись", type = "number", default = 20 },
        { key = "dedupe_values", label = "Граф: объединять одинаковые значения", type = "boolean", default = false },
        { key = "graph_include_all_fields", label = "Граф: включать все поля (шумно)", type = "boolean", default = false },
        { key = "graph_compact_fields", label = "Граф: компактные поля (группировать)", type = "boolean", default = true },
        { key = "graph_compact_max_values", label = "Граф: максимум значений в группе", type = "number", default = 8 },
        { key = "graph_skip_db_nodes", label = "Граф: не показывать узлы баз данных", type = "boolean", default = true },
        { key = "graph_filter_junk", label = "Граф: фильтровать мусорные email", type = "boolean", default = true },
    },

    ---------------------------------------------------------------------------
    -- Graph node style configuration (plugin developers may customize)
    ---------------------------------------------------------------------------
    graph_styles = {
        -- node_type = { shape, fill_color, stroke_color, text_color }
        query       = { shape = "round",   fill = "#FFD700", stroke = "#8B4513", text = "#000" },
        db          = { shape = "rect",    fill = "#C7D2FE", stroke = "#4338CA", text = "#000" },
        record      = { shape = "rect",    fill = "#E5E7EB", stroke = "#6B7280", text = "#000" },
        email       = { shape = "rect",    fill = "#ADD8E6", stroke = "#1E90FF", text = "#000" },
        phone       = { shape = "rect",    fill = "#98FB98", stroke = "#228B22", text = "#000" },
        name        = { shape = "round",   fill = "#FFDAB9", stroke = "#D2691E", text = "#000" },
        address     = { shape = "rect",    fill = "#E6E6FA", stroke = "#483D8B", text = "#000" },
        ip          = { shape = "rect",    fill = "#F08080", stroke = "#8B0000", text = "#000" },
        username    = { shape = "hexagon", fill = "#DDA0DD", stroke = "#8B008B", text = "#000" },
        password    = { shape = "diamond", fill = "#FF6B6B", stroke = "#CC0000", text = "#FFF" },
        source      = { shape = "rect",    fill = "#90EE90", stroke = "#2E8B57", text = "#000" },
        dob         = { shape = "rect",    fill = "#FFE4B5", stroke = "#FF8C00", text = "#000" },
        other       = { shape = "rect",    fill = "#CCCCCC", stroke = "#555555", text = "#000" },
    },

    -- Edge (connection line) styles
    edge_styles = {
        primary     = { line = "-->",  style = "stroke:#4A90D9,stroke-width:2px" },
        secondary   = { line = "-.->", style = "stroke:#888,stroke-width:1px" },
        depth       = { line = "==>",  style = "stroke:#E67E22,stroke-width:2px" },
        db          = { line = "-->",  style = "stroke:#4338CA,stroke-width:2px" },
        record      = { line = "-->",  style = "stroke:#6B7280,stroke-width:1px" },
    },
}

---------------------------------------------------------------------------
-- Helper functions
---------------------------------------------------------------------------

-- Normalize key: take last dot-separated segment, lowercase, strip special chars
local function key_tail(full_key)
    local tail = full_key:match("([^.]+)$") or full_key
    tail = string.lower(tostring(tail))
    tail = tail:gsub("[^%w]+", "_")
    tail = tail:gsub("^_+", ""):gsub("_+$", "")
    return tail
end

-- Extract record ID from a key: everything before the last dot
local function record_id(full_key)
    return full_key:match("^(.*)%.") or ""
end

local NAME_KEYS = {
    name = true, full_name = true, fio = true,
    fullname = true,
    firstname = true, first_name = true,
    lastname = true, last_name = true, surname = true,
    patronymic = true, middle_name = true, middlename = true,
}

local DOB_KEYS = {
    dob = true, bday = true,
    birth = true, birthday = true, birth_date = true, birthdate = true,
    date_of_birth = true, dateofbirth = true,
    data_rozhdeniya = true, data_rojdeniya = true,
}

-- Keys for generic dates (not necessarily birth dates)
local DATE_KEYS = {
    date = true, regdate = true, reg_date = true, registration_date = true,
    created = true, created_at = true, createdat = true,
    updated = true, updated_at = true,
    last_login = true, lastlogin = true, last_seen = true,
}

-- Keys for gender fields
local GENDER_KEYS = {
    gender = true, sex = true, pol = true,
}

local PHONE_KEYS = {
    phone = true, phone_number = true, phone2 = true, phone3 = true,
    workphone = true, homephone = true,
    mobile = true, mobile_phone = true, mobilephone = true,
    tel = true, telephone = true, msisdn = true,
}

local EMAIL_KEYS = {
    email = true, e_mail = true, e_mail_address = true, e_mailaddress = true,
    email_address = true, emailaddress = true,
}

local ADDRESS_KEYS = {
    address = true, addr = true, city = true, country = true,
    region = true, state = true, street = true,
    house = true, apartment = true, location = true,
}

local USERNAME_KEYS = {
    username = true, user = true, login = true, nickname = true, nick = true,
    vkid = true,
}

local PASSWORD_KEYS = {
    password = true, pass = true, pwd = true, hash = true,
}

local SOURCE_KEYS = {
    source = true, database = true, db = true, leak = true, infoleak = true,
}

local GRAPH_KEYS = {
    fullname = true, firstname = true, lastname = true, surname = true, patronymic = true,
    name = true, fio = true,
    phone = true, phone_number = true, phone2 = true, phone3 = true, workphone = true, homephone = true,
    mobile = true, mobile_phone = true, mobilephone = true, tel = true, telephone = true, msisdn = true,
    email = true, e_mail = true,
    bday = true, dob = true, birth = true, birthday = true, birthdate = true,
    date = true, regdate = true, reg_date = true, created = true, created_at = true,
    address = true, addr = true, city = true, region = true, country = true, street = true, house = true, apartment = true, location = true,
    nickname = true, username = true, login = true, nick = true, vkid = true,
    passportseries = true, passportnumber = true, passport = true,
    accountnumber = true,
    autonumber = true, vin = true, autobrand = true, issueyear = true,
    ip = true, url = true, link = true,
    gender = true, sex = true, age = true,
}

local function should_include_field(full_key, include_all)
    if include_all then return true end
    local tail = key_tail(full_key)
    return GRAPH_KEYS[tail] or false
end

local function row_value_by_keys(row, keyset)
    for k, v in pairs(row) do
        local tail = key_tail(tostring(k))
        if keyset[tail] and v ~= nil and v ~= "" then
            return tostring(v), tail
        end
    end
    return nil, nil
end

local utf8_truncate

local function build_record_label(row, index)
    local v = row_value_by_keys(row, NAME_KEYS)
    if v then return utf8_truncate(v, 40) end
    v = row_value_by_keys(row, EMAIL_KEYS)
    if v then return utf8_truncate(v, 40) end
    v = row_value_by_keys(row, PHONE_KEYS)
    if v then return utf8_truncate(v, 40) end
    return "Record #" .. tostring(index)
end

local BUCKET_LABELS = {
    name = "Names",
    email = "Emails",
    phone = "Phones",
    address = "Addresses",
    dob = "Birth Dates",
    date = "Dates",
    gender = "Gender",
    username = "Usernames",
    ip = "IP",
    url = "Links",
    passport = "Passport",
    account = "Accounts",
    auto = "Auto",
    other = "Other",
}

local BUCKET_NODE_TYPES = {
    name = "Person",
    email = "Email",
    phone = "Phone",
    address = "Address",
    dob = "Custom",
    date = "Custom",
    gender = "Custom",
    username = "Person",
    ip = "IP",
    url = "Website",
    passport = "Document",
    account = "Document",
    auto = "Custom",
    other = "Custom",
}

local BUCKET_STYLE_KEYS = {
    name = "name",
    email = "email",
    phone = "phone",
    address = "address",
    dob = "dob",
    date = "dob",
    gender = "other",
    username = "username",
    ip = "ip",
    url = "other",
    passport = "source",
    account = "source",
    auto = "other",
    other = "other",
}

local detect_data_type

local function bucket_for_field(key, value)
    local tail = key_tail(tostring(key))
    local dt = detect_data_type(key, value)

    if tail == "autonumber" or tail == "vin" or tail == "autobrand" or tail == "issueyear" then
        return "auto"
    end
    if tail == "passportseries" or tail == "passportnumber" or tail == "passport" then
        return "passport"
    end
    if tail == "accountnumber" then
        return "account"
    end
    if tail == "url" or tail == "link" then
        return "url"
    end

    return dt or "other"
end

local function add_unique_value(list, set, value, max_len)
    if not value or value == "" then return end
    if set[value] then return end
    set[value] = true
    if max_len and max_len > 0 then
        value = utf8_truncate(value, max_len)
    end
    list[#list + 1] = value
end

-- Blocklist of junk/test email addresses (lowercase patterns)
local JUNK_EMAIL_PATTERNS = {
    "^test@", "^test%d*@", "^example@", "^user@", "^admin@", "^info@example%.",
    "^no%-?reply@", "^noreply@", "^null@", "^root@", "^postmaster@",
    "^mail@mail%.", "^email@email%.", "^a@", "^aa@", "^aaa@",
    "^asdf@", "^qwerty@", "^123@", "^sample@", "^demo@",
}
local JUNK_EMAIL_DOMAINS = {
    ["example.com"] = true, ["example.org"] = true, ["example.net"] = true,
    ["test.com"] = true, ["test.ru"] = true, ["test.test"] = true,
    ["mail.mail"] = true, ["email.email"] = true,
    ["domain.com"] = true, ["domain.ru"] = true,
    ["localhost"] = true, ["localhost.localdomain"] = true,
}

local function is_junk_email(value)
    local v = string.lower(value)
    local domain = v:match("@(.+)$")
    if domain and JUNK_EMAIL_DOMAINS[domain] then return true end
    -- Check pattern blocklist
    for _, pat in ipairs(JUNK_EMAIL_PATTERNS) do
        if v:match(pat) then return true end
    end
    return false
end

local function is_email_value(value)
    if not value or value == "" then return false end
    if value:find("%s") then return false end
    local v = string.lower(value)
    if #v < 6 or #v > 254 then return false end
    if not v:match("^[%w%._%+%-]+@[%w%-%.]+%.[a-z][a-z%.]*$") then return false end
    if is_junk_email(v) then return false end
    return true
end

local function is_phone_value(value)
    if not value or value == "" then return false end
    local v = tostring(value)
    -- Phone must start with +, 8, 7 or contain parentheses/dashes
    -- First rule out IP addresses (four dot-separated groups)
    if v:match("^%d+%.%d+%.%d+%.%d+$") then return false end
    -- Rule out dates (digits separated by dots/slashes in date format)
    if v:match("^%d%d[%./-]%d%d[%./-]%d%d%d?%d?$") then return false end
    if v:match("^%d%d%d%d[%./-]%d%d[%./-]%d%d$") then return false end
    -- Phone: starts with +, or contains parentheses/dashes, or is 10-15 raw digits
    local digits = v:gsub("%D", "")
    if #digits < 7 or #digits > 15 then return false end
    -- Starts with + → almost certainly a phone number
    if v:match("^%+") then return true end
    -- Contains typical phone formatting: parentheses, dashes, spaces between digits
    if v:match("%(%d+%)") or v:match("%d[%-%s]%d") then return true end
    -- Raw digits only: accept 10-15 digits (7-9 without formatting is too ambiguous — could be an ID)
    if v:match("^%d+$") then
        if #digits >= 10 and #digits <= 15 then return true end
        -- 7-9 digits with no formatting — too risky to classify as phone
        return false
    end
    -- Starts with 8 or 7 followed by a separator (Russian format)
    if v:match("^[78]%D?%d") and #digits >= 10 then return true end
    return false
end

local function is_date_value(value)
    if not value or value == "" then return false end
    -- Strict date format matching with range validation for day/month
    local d, m, y
    -- DD.MM.YYYY
    d, m, y = value:match("^(%d%d)%.(%d%d)%.(%d%d%d%d)$")
    if d then
        d, m, y = tonumber(d), tonumber(m), tonumber(y)
        if d >= 1 and d <= 31 and m >= 1 and m <= 12 and y >= 1900 and y <= 2030 then return true end
    end
    -- YYYY-MM-DD
    y, m, d = value:match("^(%d%d%d%d)%-(%d%d)%-(%d%d)$")
    if y then
        d, m, y = tonumber(d), tonumber(m), tonumber(y)
        if d >= 1 and d <= 31 and m >= 1 and m <= 12 and y >= 1900 and y <= 2030 then return true end
    end
    -- DD/MM/YYYY
    d, m, y = value:match("^(%d%d)/(%d%d)/(%d%d%d%d)$")
    if d then
        d, m, y = tonumber(d), tonumber(m), tonumber(y)
        if d >= 1 and d <= 31 and m >= 1 and m <= 12 and y >= 1900 and y <= 2030 then return true end
    end
    -- YYYY/MM/DD
    y, m, d = value:match("^(%d%d%d%d)/(%d%d)/(%d%d)$")
    if y then
        d, m, y = tonumber(d), tonumber(m), tonumber(y)
        if d >= 1 and d <= 31 and m >= 1 and m <= 12 and y >= 1900 and y <= 2030 then return true end
    end
    return false
end

local function is_ip_value(value)
    if not value or value == "" then return false end
    local a, b, c, d = value:match("^(%d+)%.(%d+)%.(%d+)%.(%d+)$")
    if not a then
        -- IPv4 with port (e.g. 192.168.1.1:8080)
        a, b, c, d = value:match("^(%d+)%.(%d+)%.(%d+)%.(%d+):%d+$")
    end
    if not a then return false end
    a, b, c, d = tonumber(a), tonumber(b), tonumber(c), tonumber(d)
    return a and b and c and d and a <= 255 and b <= 255 and c <= 255 and d <= 255
end

local function is_name_value(value)
    if not value or value == "" then return false end
    local v = tostring(value)
    -- Names must not contain digits, @, or slashes
    if v:find("%d") or v:find("@") or v:find("/") then return false end
    -- Not an email, IP, or URL (single word ending with dots)
    if v:find("%.%a%a+$") and not v:find("%s") then return false end
    -- Count words (for Cyrillic, #w counts bytes; one Cyrillic char = 2 bytes)
    local words = {}
    for w in v:gmatch("%S+") do
        if #w >= 2 then
            words[#words + 1] = w
        end
    end
    -- Full name: 1-4 words (single word is allowed for surnames / first names)
    if #words < 1 or #words > 4 then return false end
    -- Each word must start with a letter (upper or lower case)
    -- Lowercase is permitted — leaks often have "alexey shevtsov"
    for _, w in ipairs(words) do
        local b1 = string.byte(w, 1)
        -- Latin letter A-Z or a-z
        if (b1 >= 65 and b1 <= 90) or (b1 >= 97 and b1 <= 122) then
            -- OK
        -- Cyrillic (UTF-8: first byte is D0 or D1)
        elseif b1 == 0xD0 or b1 == 0xD1 then
            -- OK — Cyrillic character
        else
            return false
        end
    end
    -- Value is too short (< 3 bytes) — treat as junk
    if #v < 3 then return false end
    return true
end

-- Strict check: value is a full name (2+ words composed of letters)
local function is_fio_value(value)
    if not is_name_value(value) then return false end
    local words = {}
    for w in tostring(value):gmatch("%S+") do
        if #w >= 2 then words[#words + 1] = w end
    end
    return #words >= 2
end

-- Check whether a value looks like an address or location
local function is_address_value(value)
    if not value or value == "" then return false end
    local v = tostring(value)
    if v:match("^%d+$") then return false end -- bare number
    if #v < 4 then return false end -- too short ("UA", "nsk")
    if is_email_value(v) or is_ip_value(v) then return false end
    -- 2-3 letter country codes (US, RU, UA, USA) — too generic to be useful
    if v:match("^%a%a%a?$") then return false end
    return true
end

-- Check whether a value looks like a username or login
local function is_username_value(value)
    if not value or value == "" then return false end
    local v = tostring(value)
    if #v < 2 or #v > 64 then return false end
    if v:find("@") then return false end
    if v:match("^%d+$") then return false end
    if is_ip_value(v) then return false end
    return true
end

-- Build a CSS style string for a node from the style table
local function make_node_style(style_entry)
    if not style_entry then
        style_entry = plugin.graph_styles.other
    end
    return string.format(
        "fill:%s,stroke:%s,stroke-width:2px,color:%s",
        style_entry.fill, style_entry.stroke, style_entry.text
    )
end

-- UTF-8-safe string truncation (string.sub cuts by byte and corrupts Cyrillic)
utf8_truncate = function(s, max_chars)
    if not s then return "" end
    local len = 0
    local i = 1
    local byte_len = #s
    while i <= byte_len and len < max_chars do
        local b = string.byte(s, i)
        if b < 128 then
            i = i + 1
        elseif b < 224 then
            i = i + 2
        elseif b < 240 then
            i = i + 3
        else
            i = i + 4
        end
        len = len + 1
    end
    if i <= byte_len then
        return string.sub(s, 1, i - 1) .. "..."
    end
    return s
end

-- UTF-8-safe filename builder: keep ASCII chars, space -> "_", preserve UTF-8 sequences
local function safe_filename_from(text, fallback)
    local safe_parts = {}
    local i = 1
    local len = #text
    while i <= len do
        local b = string.byte(text, i)
        if (b >= 48 and b <= 57) or (b >= 65 and b <= 90) or (b >= 97 and b <= 122)
           or b == 45 or b == 95 or b == 46 then
            safe_parts[#safe_parts + 1] = string.char(b)
            i = i + 1
        elseif b == 32 then
            safe_parts[#safe_parts + 1] = "_"
            i = i + 1
        elseif b >= 0xC0 then
            local char_len = (b < 0xE0) and 2 or (b < 0xF0) and 3 or 4
            safe_parts[#safe_parts + 1] = string.sub(text, i, i + char_len - 1)
            i = i + char_len
        else
            i = i + 1
        end
    end
    local safe = table.concat(safe_parts)
    if safe == "" then safe = fallback or "file" end
    return safe
end

-- Check whether a value is a date/time in any supported format (for regdate, created_at, etc.)
local function is_datetime_value(value)
    if not value or value == "" then return false end
    -- Strict date formats (is_date_value already handles these)
    if is_date_value(value) then return true end
    -- YYYY-MM-DD HH:MM:SS (with optional milliseconds)
    if value:match("^%d%d%d%d%-%d%d%-%d%d%s+%d%d:%d%d") then return true end
    -- Unix timestamp in milliseconds (13 digits) or seconds (10 digits)
    if value:match("^%d%d%d%d%d%d%d%d%d%d%d?%d?%d?$") then
        local n = tonumber(value)
        -- 946684800 = 2000-01-01, sanity range
        if n and ((n > 946684800 and n < 2000000000) or (n > 946684800000 and n < 2000000000000)) then
            return true
        end
    end
    return false
end

-- Check whether a value represents a gender
local function is_gender_value(value)
    if not value or value == "" then return false end
    local v = string.lower(tostring(value))
    return v == "m" or v == "f" or v == "male" or v == "female"
        or v == "м" or v == "ж" or v == "мужской" or v == "женский"
        or v == "муж" or v == "жен"
end

-- Check whether a value is junk and should be excluded from the graph
local function is_junk_value(value)
    if not value or value == "" then return true end
    local v = tostring(value)
    local vl = string.lower(v)
    -- Known junk/placeholder strings
    if vl == "0" or vl == "null" or vl == "none" or vl == "n/a" or vl == "-"
       or vl == "nan" or vl == "undefined" or vl == "true" or vl == "false" then
        return true
    end
    -- 1-3 digit numbers (IDs, ages, indices) with no context are too ambiguous
    if v:match("^%d%d?%d?$") then return true end
    return false
end

-- Detect data type by field key + value (strict heuristics, applied in priority order)
detect_data_type = function(key, value)
    local k = key_tail(tostring(key))
    local v = tostring(value)

    -- 0) Junk values — skip immediately
    if is_junk_value(v) then return "other" end

    -- 1) IP — checked FIRST, before phone (otherwise IPs get mis-classified as phones)
    if is_ip_value(v) then return "ip" end

    -- 2) Email — strict format check on the value itself
    if is_email_value(v) then return "email" end

    -- 3) Date of birth — DOB key + valid date format
    if DOB_KEYS[k] and is_date_value(v) then return "dob" end

    -- 4) Other dates (regdate, created_at) — DATE key + datetime format
    if DATE_KEYS[k] and is_datetime_value(v) then return "date" end

    -- 5) Gender
    if GENDER_KEYS[k] and is_gender_value(v) then return "gender" end

    -- 6) Phone — matching key + format, OR starts with + (international) without a key
    if PHONE_KEYS[k] and is_phone_value(v) then return "phone" end
    if not PHONE_KEYS[k] and v:match("^%+%d") and is_phone_value(v) then return "phone" end

    -- 7) Full name — USERNAME/NAME key + value looks like a full name (2+ words)
    --    Priority: if the value looks like a full name, classify as "name" even if the key says "username"
    if is_fio_value(v) and (NAME_KEYS[k] or USERNAME_KEYS[k]) then return "name" end

    -- 8) Name by key (single word also accepted — surname, firstname)
    if NAME_KEYS[k] and is_name_value(v) then return "name" end

    -- 9) Address — matching key + non-junk value
    if ADDRESS_KEYS[k] and is_address_value(v) then return "address" end

    -- 10) Username — matching key + login-like value (full names already handled above)
    if USERNAME_KEYS[k] and is_username_value(v) then return "username" end

    -- 11) Password — key match only
    if PASSWORD_KEYS[k] and v ~= "" then return "password" end

    -- 12) Source — key match only
    if SOURCE_KEYS[k] and v ~= "" then return "source" end

    -- 13) Value-only fallback (no key match)
    if is_date_value(v) then return "date" end
    -- Full name without a matching key — not inferred (too many false positives)

    return "other"
end

-- Map data_type -> node_type for the graph model (Person, Email, Phone, etc.)
local function data_type_to_node_type(dt)
    local map = {
        email    = "Email",
        phone    = "Phone",
        name     = "Person",
        address  = "Address",
        ip       = "IP",
        username = "Person",
        password = "Custom",
        source   = "Document",
        dob      = "Custom",
        other    = "Custom",
        query    = "Person",
        db       = "Document",
        record   = "Document",
    }
    return map[dt] or "Custom"
end

-- Send a single request to the LeakOSINT API
local function do_search(query_text, token, limit, lang, report_type)
    local payload_table = {
        token   = token,
        request = query_text,
        limit   = limit,
        lang    = lang,
        type    = report_type,
    }

    local payload, err = host:json_encode(payload_table)
    if not payload then return nil, err end

    local body, err = host:http_post("https://leakosintapi.com/", payload, 30, nil, "application/json")
    if not body then return nil, err end

    local data, err = host:json_decode(body)
    if not data then return nil, err end

    if type(data) ~= "table" then return nil, "Неожиданный формат ответа" end
    if data.error then return nil, tostring(data.error) end

    return data
end

-- Recursively extract key=value pairs from nested tables
local function extract_fields(tbl, prefix, results)
    prefix = prefix or ""
    results = results or {}

    if type(tbl) ~= "table" then
        return results
    end

    -- Iterate whether array (1-based) or dictionary
    for k, v in pairs(tbl) do
        local full_key = prefix ~= "" and (prefix .. "." .. tostring(k)) or tostring(k)

        if type(v) == "table" then
            extract_fields(v, full_key, results)
        else
            local sv = tostring(v)
            if sv ~= "" and sv ~= "nil" and sv ~= "true" and sv ~= "false" then
                results[#results + 1] = { key = full_key, value = sv }
            end
        end
    end

    return results
end

-- Extract values suitable for follow-up searches (depth level 1)
local function extract_searchable(fields, max_queries, allow_name_only)
    local searchable = {}
    local seen = {}
    local names_by_record = {}
    local dobs_by_record = {}

    local function add_query(q, qtype, label)
        if not q or q == "" then return false end
        if seen[q] then return false end
        if max_queries and #searchable >= max_queries then return false end
        seen[q] = true
        searchable[#searchable + 1] = { query = q, type = qtype, label = label or q }
        return true
    end

    local function add_to_record(map, rid, value)
        local t = map[rid]
        if not t then
            t = {}
            map[rid] = t
        end
        t[#t + 1] = value
    end

    -- 1) Collect high-confidence email/phone values (with junk filtering)
    for _, f in ipairs(fields) do
        if f.key:find("%.Data%.") then
            local v = f.value
            if is_email_value(v) and not is_junk_email(v) then
                add_query(v, "email", v)
            elseif is_phone_value(v) then
                add_query(v, "phone", v)
            end
        end
    end

    -- 2) Collect full names and dates of birth grouped by record
    for _, f in ipairs(fields) do
        if f.key:find("%.Data%.") then
            local tail = key_tail(f.key)
            local rid = record_id(f.key)
            local v = f.value

            if NAME_KEYS[tail] and is_name_value(v) then
                add_to_record(names_by_record, rid, v)
            elseif DOB_KEYS[tail] and is_date_value(v) then
                add_to_record(dobs_by_record, rid, v)
            end
        end
    end

    -- 3) Combine full name + date of birth within the same record
    for rid, names in pairs(names_by_record) do
        local dobs = dobs_by_record[rid]
        if dobs and #dobs > 0 then
            for _, name in ipairs(names) do
                for _, dob in ipairs(dobs) do
                    if max_queries and #searchable >= max_queries then
                        return searchable
                    end
                    add_query(name .. " " .. dob, "name", name .. " " .. dob)
                end
            end
        elseif allow_name_only then
            for _, name in ipairs(names) do
                if max_queries and #searchable >= max_queries then
                    return searchable
                end
                add_query(name, "name", name)
            end
        end
    end

    return searchable
end


---------------------------------------------------------------------------
-- Main search function
---------------------------------------------------------------------------

function plugin.search(query, options)
    -- 1. Validate query
    if not query or query == "" then
        return nil, "Введите поисковый запрос (телефон, email, ФИО, номер авто и т.д.)."
    end

    -- 2. Read and validate API token
    local token = host:get_config("token")
    if not token or token == "" then
        return nil, "API-токен не указан! Получите его в боте LeakOSINT (/api) и впишите в настройках плагина (ПКМ -> Настройки)."
    end

    local limit            = host:get_config("limit") or 100
    local lang             = host:get_config("lang") or "ru"
    local report_type      = host:get_config("type") or "json"
    local depth            = host:get_config("depth") or 0
    local depth_max_queries = host:get_config("depth_max_queries") or 10
    local depth_name_only  = host:get_config("depth_name_only") or false
    local debug_dump       = host:get_config("debug_dump") or false
    local debug_dump_limit = host:get_config("debug_dump_limit") or 5
    local max_records_per_db = host:get_config("max_records_per_db") or 30
    local max_fields_per_record = host:get_config("max_fields_per_record") or 20
    local dedupe_values = host:get_config("dedupe_values") or false
    local graph_include_all_fields = host:get_config("graph_include_all_fields") or false
    local graph_compact_fields = host:get_config("graph_compact_fields") or false
    local graph_compact_max_values = host:get_config("graph_compact_max_values") or 8
    local graph_skip_db_nodes = host:get_config("graph_skip_db_nodes")
    local graph_filter_junk = host:get_config("graph_filter_junk")
    if graph_skip_db_nodes == nil then graph_skip_db_nodes = true end
    if graph_filter_junk == nil then graph_filter_junk = true end

    local safe_base = safe_filename_from(query, "query")

    if depth_max_queries < 0 then depth_max_queries = 0 end
    if debug_dump_limit < 0 then debug_dump_limit = 0 end
    if max_records_per_db < 0 then max_records_per_db = 0 end
    if max_fields_per_record < 0 then max_fields_per_record = 0 end
    if graph_compact_max_values < 0 then graph_compact_max_values = 0 end

    host:print("═══════════════════════════════════════════════════")
    host:print("  LeakOSINT Search v2.0  |  Глубина: " .. tostring(depth))
    host:print("═══════════════════════════════════════════════════")
    host:print("")
    host:print("Запрос: " .. query)
    host:print(string.format("Параметры: лимит=%d, язык=%s, тип=%s", limit, lang, report_type))
    host:print("")

    -- 3. Primary search (level 0)
    host:print("▶ [Уровень 0] Поиск по: " .. query)
    local data, err = do_search(query, token, limit, lang, report_type)
    if not data then
        return nil, "Ошибка поиска: " .. tostring(err)
    end

    if debug_dump then
        local raw_json, jerr = host:json_encode(data)
        if raw_json then
            local p = "debug/LeakOSINT_" .. safe_base .. "_level0.json"
            host:write_file(p, raw_json)
            host:print("Debug dump saved: " .. p)
        else
            host:print("Debug dump error: " .. tostring(jerr))
        end
    end

    -- Depth 0: return raw result without building a graph
    if depth == 0 then
        host:print("Поиск завершён (глубина 0, граф не создаётся)")
        return data
    end

    -----------------------------------------------------------------------
    -- Build relationship graph (depth >= 1)
    -----------------------------------------------------------------------
    host:print("")
    host:print("▶ Создание графа связей...")

    local graph_id = host:graph_create("LeakOSINT — " .. query, "LR")

    -- Central node representing the original query
    local style = plugin.graph_styles.query
    local center_id = host:graph_add_node(
        graph_id, query, data_type_to_node_type("query"),
        style.shape, make_node_style(style),
        "Исходный запрос"
    )

    -- Extract fields from primary results (used for depth search)
    local fields = extract_fields(data)
    host:print(string.format("  Найдено %d полей данных", #fields))

    -- Value map for deduplication
    local value_node_map = {}

    local function add_value_node(val, dt, key, map)
        local v = tostring(val)
        local label = utf8_truncate(v, 40)
        local ns = plugin.graph_styles[dt] or plugin.graph_styles.other
        local nid = host:graph_add_node(
            graph_id, label, data_type_to_node_type(dt),
            ns.shape, make_node_style(ns),
            key .. ": " .. v
        )
        if map then
            map[dt .. ":" .. v] = nid
        end
        return nid
    end

    -- Determine whether a field value should be skipped as junk
    local function should_skip_value(key, value)
        if not graph_filter_junk then return false end
        local v = tostring(value)
        if is_junk_value(v) then return true end
        if is_junk_email(v) then return true end
        -- Skip values that simply repeat the key name (e.g. value="Address" key="address")
        local tail = key_tail(tostring(key))
        local v_lower = string.lower(v)
        local key_as_value_ru = {
            address = "адрес", city = "город", country = "страна",
            region = "регион", street = "улица", house = "дом",
            name = "имя", phone = "телефон", email = "email",
            password = "пароль", login = "логин",
        }
        if key_as_value_ru[tail] and v_lower == key_as_value_ru[tail] then return true end
        return false
    end

    local function build_graph_from_data(root_id, data_obj)
        local list = data_obj and (data_obj.List or data_obj["List"])
        if type(list) ~= "table" then
            return 0, 0, 0
        end

        local db_count, rec_count, field_count = 0, 0, 0
        for db_name, db_val in pairs(list) do
            if type(db_val) == "table" then
                -- Determine parent node for records: either the DB node or the root directly
                local parent_for_records = root_id

                if not graph_skip_db_nodes then
                    local info = db_val.InfoLeak or db_val["InfoLeak"]
                    local num = db_val.NumOfResults or db_val["NumOfResults"]
                    local db_label = tostring(db_name)
                    if num ~= nil then
                        db_label = db_label .. " (" .. tostring(num) .. ")"
                    end

                    local db_style = plugin.graph_styles.db
                    local db_id = host:graph_add_node(
                        graph_id, db_label, data_type_to_node_type("db"),
                        db_style.shape, make_node_style(db_style),
                        info and utf8_truncate(tostring(info), 200) or ""
                    )
                    db_count = db_count + 1

                    local edge_db = plugin.edge_styles.db
                    host:graph_add_edge(
                        graph_id, root_id, db_id,
                        "DB", "Connected",
                        edge_db.line, edge_db.style
                    )
                    parent_for_records = db_id
                end

                local data_list = db_val.Data or db_val["Data"]
                if type(data_list) == "table" then
                    local added_records = 0
                    for idx, row in ipairs(data_list) do
                        if max_records_per_db > 0 and added_records >= max_records_per_db then
                            break
                        end
                        if type(row) == "table" then
                            added_records = added_records + 1
                            local rec_label = build_record_label(row, idx)
                            local rec_style = plugin.graph_styles.record
                            local rec_id = host:graph_add_node(
                                graph_id, rec_label, data_type_to_node_type("record"),
                                rec_style.shape, make_node_style(rec_style),
                                tostring(db_name) .. " #" .. tostring(idx)
                            )
                            rec_count = rec_count + 1

                            local edge_rec = plugin.edge_styles.record
                            host:graph_add_edge(
                                graph_id, parent_for_records, rec_id,
                                graph_skip_db_nodes and tostring(db_name) or "Record",
                                "RelatedTo",
                                edge_rec.line, edge_rec.style
                            )

                            if graph_compact_fields then
                                -- Compact mode: group fields into buckets
                                -- For addresses, merge all related sub-fields into a single label
                                local buckets = {}
                                local bucket_sets = {}

                                for k, v in pairs(row) do
                                    local sv = tostring(v)
                                    if v ~= nil and sv ~= "" and should_include_field(tostring(k), graph_include_all_fields) then
                                        if not should_skip_value(k, v) then
                                            local bucket = bucket_for_field(k, v) or "other"
                                            if not buckets[bucket] then
                                                buckets[bucket] = {}
                                                bucket_sets[bucket] = {}
                                            end
                                            -- For addresses: store "key: value" pairs so the label stays readable
                                            if bucket == "address" then
                                                local tail = key_tail(tostring(k))
                                                add_unique_value(buckets[bucket], bucket_sets[bucket], tail .. ": " .. sv, 80)
                                            else
                                                add_unique_value(buckets[bucket], bucket_sets[bucket], sv, 80)
                                            end
                                        end
                                    end
                                end

                                for bucket, values in pairs(buckets) do
                                    if #values > 0 then
                                        -- For addresses: use field values as label instead of "Addresses (N)"
                                        local label
                                        if bucket == "address" then
                                            -- Concatenate all address sub-fields into a single line
                                            local addr_parts = {}
                                            for _, av in ipairs(values) do
                                                -- Strip "key: " prefix for the display label
                                                local clean = av:match("^[^:]+:%s*(.+)$") or av
                                                addr_parts[#addr_parts + 1] = clean
                                            end
                                            label = utf8_truncate(table.concat(addr_parts, ", "), 60)
                                        else
                                            label = (BUCKET_LABELS[bucket] or bucket) .. " (" .. tostring(#values) .. ")"
                                        end

                                        local node_type = BUCKET_NODE_TYPES[bucket] or "Custom"
                                        local style_key = BUCKET_STYLE_KEYS[bucket] or "other"
                                        local ns = plugin.graph_styles[style_key] or plugin.graph_styles.other

                                        local desc_vals = values
                                        if graph_compact_max_values > 0 and #values > graph_compact_max_values then
                                            desc_vals = {}
                                            for i = 1, graph_compact_max_values do
                                                desc_vals[#desc_vals + 1] = values[i]
                                            end
                                            desc_vals[#desc_vals + 1] = "... +" .. tostring(#values - graph_compact_max_values)
                                        end
                                        local desc = table.concat(desc_vals, "\n")

                                        local nid = host:graph_add_node(
                                            graph_id, label, node_type,
                                            ns.shape, make_node_style(ns),
                                            desc
                                        )

                                        local edge_s = plugin.edge_styles.primary
                                        host:graph_add_edge(
                                            graph_id, rec_id, nid,
                                            BUCKET_LABELS[bucket] or bucket, "RelatedTo",
                                            edge_s.line, edge_s.style
                                        )
                                        field_count = field_count + 1
                                    end
                                end
                            else
                                local added_fields = 0
                                for k, v in pairs(row) do
                                    if max_fields_per_record > 0 and added_fields >= max_fields_per_record then
                                        break
                                    end
                                    local sv = tostring(v)
                                    if v ~= nil and sv ~= "" and should_include_field(tostring(k), graph_include_all_fields) then
                                        if not should_skip_value(k, v) then
                                            local dt = detect_data_type(k, v)
                                            local key = tostring(k)
                                            local val = sv
                                            local nid = nil
                                            if dedupe_values then
                                                local map_key = dt .. ":" .. val
                                                nid = value_node_map[map_key]
                                                if not nid then
                                                    nid = add_value_node(val, dt, key, value_node_map)
                                                end
                                            else
                                                nid = add_value_node(val, dt, key, nil)
                                            end

                                            local edge_s = plugin.edge_styles.primary
                                            host:graph_add_edge(
                                                graph_id, rec_id, nid,
                                                key, "RelatedTo",
                                                edge_s.line, edge_s.style
                                            )
                                            added_fields = added_fields + 1
                                            field_count = field_count + 1
                                        end
                                    end
                                end
                            end
                        end
                    end
                end
            end
        end

        return db_count, rec_count, field_count
    end

    local db_count, rec_count, field_count = build_graph_from_data(center_id, data)
    host:print(string.format("  Граф: БД=%d, записей=%d, полей=%d", db_count, rec_count, field_count))

    -----------------------------------------------------------------------
    -- Depth 1: follow-up searches on extracted data values
    -----------------------------------------------------------------------
    if depth >= 1 then
        local searchable = extract_searchable(fields, depth_max_queries, depth_name_only)
        host:print(string.format("\n▶ [Уровень 1] Найдено %d запросов для углублённого поиска", #searchable))

        for i, sq in ipairs(searchable) do
            host:print(string.format("  [%d/%d] Поиск по: %s (%s)", i, #searchable, sq.query, sq.type))

            -- Brief pause between requests to avoid overloading the API
            if i > 1 then host:sleep(1) end

            local sub_data, sub_err = do_search(sq.query, token, limit, lang, report_type)
            if sub_data and type(sub_data) == "table" then
                if debug_dump and i <= debug_dump_limit then
                    local sub_json, sjerr = host:json_encode(sub_data)
                    if sub_json then
                        local p = "debug/LeakOSINT_" .. safe_base .. "_level1_" .. tostring(i) .. ".json"
                        host:write_file(p, sub_json)
                        host:print("Debug dump saved: " .. p)
                    else
                        host:print("Debug dump error (level1): " .. tostring(sjerr))
                    end
                end
                local sq_style = plugin.graph_styles[sq.type] or plugin.graph_styles.other
                local sq_node_id = host:graph_add_node(
                    graph_id, sq.label, data_type_to_node_type(sq.type),
                    sq_style.shape, make_node_style(sq_style),
                    "Подзапрос уровня 1"
                )

                local parent_id = center_id
                if dedupe_values then
                    local map_key = sq.type .. ":" .. sq.query
                    if value_node_map[map_key] then
                        parent_id = value_node_map[map_key]
                    end
                end

                local edge_s = plugin.edge_styles.depth
                host:graph_add_edge(
                    graph_id, parent_id, sq_node_id,
                    "Depth 1", "RelatedTo",
                    edge_s.line, edge_s.style
                )

                local db_c, rec_c, field_c = build_graph_from_data(sq_node_id, sub_data)
                host:print(string.format("    → Граф: БД=%d, записей=%d, полей=%d", db_c, rec_c, field_c))
            else
                host:print("    → Ошибка: " .. tostring(sub_err or "нет данных"))
            end
        end
    end

    -----------------------------------------------------------------------
    -- Save graph to file
    -----------------------------------------------------------------------
    local safe_query = safe_filename_from(query, "graph")
    local filename = "LeakOSINT_" .. safe_query .. ".graph.json"
    local filepath, save_err = host:graph_save(graph_id, filename)

    if filepath then
        host:print("")
        host:print("═══════════════════════════════════════════════════")
        host:print("  Граф сохранён: " .. filepath)
        host:print("═══════════════════════════════════════════════════")
    else
        host:print("[ОШИБКА] Не удалось сохранить граф: " .. tostring(save_err))
    end

    -- Return primary data so it is displayed as JSON in the output area
    return data
end

return plugin
