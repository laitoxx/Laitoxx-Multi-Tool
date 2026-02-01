"""
 @@@  @@@  @@@@@@  @@@@@@@ @@@@@@@  @@@@@@@  @@@ @@@@@@@@ @@@ @@@
 @@!  @@@ @@!  @@@   @@!   @@!  @@@ @@!  @@@ @@! @@!      @@! !@@
 @!@!@!@! @!@  !@!   @!!   @!@  !@! @!@!!@!  !!@ @!!!:!    !@!@! 
 !!:  !!! !!:  !!!   !!:   !!:  !!! !!: :!!  !!: !!:        !!:  
  :   : :  : :. :     :    :: :  :   :   : : :    :         .:   
                                                                 
    HOTDRIFY cooked with the refactor for the LAITOXX squad.
                    github.com/hotdrify
                      t.me/hotdrify

                    github.com/laitoxx
                      t.me/laitoxx
"""

import csv
import hashlib
import json
import re
from io import StringIO
from typing import Dict, List, Optional, Tuple
from collections.abc import Callable, Sequence

import requests
from bs4 import BeautifulSoup

from ..shared_utils import Color

OK_LOGIN_URL = (
    "https://www.ok.ru/dk?st.cmd=anonymMain&st.accRecovery=on&st.error=errors.password.wrong"
)
OK_RECOVER_URL = (
    "https://www.ok.ru/dk?st.cmd=anonymRecoveryAfterFailedLogin&st._aid=LeftColumn_Login_ForgotPassword"
)

API_URL = "https://api.proxynova.com/comb"
LIMIT = 100
REQUEST_TIMEOUT = 10

WHITE_LIST_KEYS: Sequence[str] = (
    "cdek_full_name",
    "cdek_email",
    "lnmatch_last_name",
    "yandex_name",
    "yandex_address_city",
    "yandex_place_name",
    "yandex_address_doorcode",
    "beeline_full_name",
    "beeline_address_city",
    "vk_email",
    "avito_user_name",
    "avito_ad_title",
    "avito_city",
    "rfcont_name",
    "rfcont_email",
    "pikabu_email",
)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/119.0 Safari/537.36"
}


def _log_separator(log: Callable[[str], None]) -> None:
    log("-" * 60)


def _extract_links_from_response(url: str, log: Callable[[str], None]) -> list[str]:
    try:
        response = requests.get(
            url, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        log(f"[!] Ошибка при запросе {url}: {exc}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    links: list[str] = []
    for result in soup.find_all("a"):
        href = result.get("href") or ""
        if href.startswith("/url?q="):
            link = href.replace("/url?q=", "").split("&")[0]
            if not any(domain in link for domain in ("google.com", "schema.org")):
                links.append(link)
    return links


def fetch_data(query: str) -> list[str]:
    try:
        response = requests.get(
            f"{API_URL}?query={query}&start=0&limit={LIMIT}",
            allow_redirects=False,
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code in {301, 302}:
            return [f"[ERROR] Переадресация обнаружена (HTTP {response.status_code})"]
        response.raise_for_status()
        data = response.json()
        return data.get("lines", ["[SORRY] Нет результатов."])
    except requests.RequestException as exc:
        return [f"[ERROR] Ошибка при запросе: {exc}"]


def format_results(results: Sequence[str]) -> str:
    formatted_results: list[str] = []
    for item in results:
        if ":" in item:
            email, password = item.split(":", 1)
            formatted_results.append(
                f"Почта: {email.strip()}\nПароль: {password.strip()}"
            )
        else:
            formatted_results.append(item)
    return "\n\n".join(formatted_results)


def google_search(
    info_name: str = "",
    info_email: str = "",
    phone: str = "",
    log: Callable[[str], None] = print,
) -> None:
    if not info_name and not info_email and not phone:
        return

    url_list: list[str] = []
    if info_name and not info_email and not phone:
        url_list = [
            f"https://www.google.com/search?q=intext:{info_name}",
            f"https://yandex.com/search/?text={info_name}",
            f"https://www.google.com/search?q={info_name}",
            f"https://yandex.com/search/?={info_name}",
        ]
    elif not info_name and info_email and not phone:
        url_list = [
            f"https://www.google.com/search?q=intext:{info_email}",
            f"https://yandex.com/search/?text={info_email}",
            f"https://www.google.com/search?q={info_email}",
            f"https://yandex.com/search/?={info_email}",
        ]
    elif info_name and info_email and not phone:
        url_list = [
            f"https://www.google.com/search?q=intext:{info_name} {info_email}",
            f"https://yandex.com/search/?text={info_name} {info_email}",
            f"https://www.google.com/search?q={info_name} {info_email}",
            f"https://yandex.com/search/?={info_name} {info_email}",
        ]
    elif info_name and info_email and phone:
        url_list = [
            f"https://www.google.com/search?q=intext:{info_name} {info_email} {phone}",
            f"https://yandex.com/search/?text={info_name} {info_email} {phone}",
            f"https://www.google.com/search?q={info_name} {info_email} {phone}",
            f"https://yandex.com/search/?={info_name} {info_email} {phone}",
        ]
    elif phone:
        url_list = [
            f"https://www.google.com/search?q=intext:{phone}",
            f"https://yandex.com/search/?text={phone}",
        ]

    for url in url_list:
        log(f"Поиск: {url}")
        links = _extract_links_from_response(url, log)
        if links:
            for link in links[:10]:
                log(f"  - {link}")
        else:
            log("  Ссылок не найдено")


def check_login(
    login_data: str, log: Callable[[str], None] = print
) -> dict[str, str | None] | None:
    session = requests.Session()
    try:
        session.get(
            f"{OK_LOGIN_URL}&st.email={login_data}",
            headers=DEFAULT_HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        request = session.get(
            OK_RECOVER_URL, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT
        )
    except requests.RequestException as exc:
        log(f"[!] Ошибка запроса к OK.ru: {exc}")
        return None

    root_soup = BeautifulSoup(request.content, "html.parser")
    soup = root_soup.find(
        "div", {"data-l": "registrationContainer,offer_contact_rest"})
    if soup:
        account_info = soup.find(
            "div", {"class": "ext-registration_tx taCenter"})
        masked_email = soup.find("button", {"data-l": "t,email"})
        masked_phone = soup.find("button", {"data-l": "t,phone"})

        masked_phone_text = None
        masked_email_text = None
        masked_name = None
        profile_info = None
        profile_registered = None

        if masked_phone:
            masked_phone_text = (
                masked_phone.find(
                    "div", {"class": "ext-registration_stub_small_header"})
            ).get_text()

        if masked_email:
            masked_email_text = (
                masked_email.find(
                    "div", {"class": "ext-registration_stub_small_header"})
            ).get_text()

        if account_info:
            masked_name_tag = account_info.find(
                "div", {"class": "ext-registration_username_header"}
            )
            if masked_name_tag:
                masked_name = masked_name_tag.get_text()

            account_info_divs = account_info.find_all(
                "div", {"class": "lstp-t"})
            if account_info_divs:
                profile_info = account_info_divs[0].get_text()
                if len(account_info_divs) > 1:
                    profile_registered = account_info_divs[1].get_text()

        if masked_name and masked_email_text:
            google_search(masked_name, masked_email_text, login_data, log=log)

        return {
            "name": masked_name,
            "email": masked_email_text,
            "phone": masked_phone_text,
            "profile": profile_info,
            "registered": profile_registered,
        }

    if root_soup.find("div", {"data-l": "registrationContainer,home_rest"}):
        return {"status": "not associated"}
    return None


def console_output(
    parsed_response: dict[str, str | None] | None,
    log: Callable[[str], None] = print,
) -> None:
    if not parsed_response:
        log("Сервер вернул неизвестный ответ")
        return
    if parsed_response.get("status") == "not associated":
        log("Номер не привязан к OK.ru")
        return
    for key, value in parsed_response.items():
        if value:
            log(f"{key.capitalize()}: {value}")


def phone_number_lookup(number: str, log: Callable[[str], None] = print) -> None:
    api_url = f"http://phone-number-api.com/json/?number={number}"
    try:
        response = requests.get(api_url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        phone_rsp = json.loads(response.text)
    except requests.RequestException as exc:
        log(f"[!] Ошибка при запросе телефонных данных: {exc}")
        return
    except json.JSONDecodeError:
        log("[!] Не удалось обработать ответ phone-number-api.com")
        return

    is_valid = str(phone_rsp.get("numberValid", "")).lower() == "true"
    if not is_valid:
        log("[!] Недействительный номер телефона")
        return

    fields: tuple[tuple[str, str], ...] = (
        ("Phone Number", phone_rsp.get("query")),
        ("Exists", phone_rsp.get("numberValid")),
        ("Phone Number Type", phone_rsp.get("numberType")),
        ("Area Code", phone_rsp.get("numberAreaCode")),
        ("Provider", phone_rsp.get("carrier")),
        ("Continent", phone_rsp.get("continent")),
        ("Country", phone_rsp.get("countryName")),
        ("Latitude (not consistent)", phone_rsp.get("lat")),
        ("Longitude (not consistent)", phone_rsp.get("lon")),
        ("Timezone", phone_rsp.get("timezone")),
    )
    for label, value in fields:
        log(f"{label}: {value}")


def google_search_phone(phone: str, log: Callable[[str], None] = print) -> None:
    url_list = [
        f"https://www.google.com/search?q=intext:+{phone}",
        f"https://yandex.com/search/?text=+{phone}",
        f"https://www.google.com/search?q=+{phone}",
        f"https://yandex.com/search/?=text+{phone}",
    ]
    for url in url_list:
        log(f"Поиск по ссылке: {url}")
        links = _extract_links_from_response(url, log)
        if links:
            log("Ссылки найдены:")
            for link in links[:10]:
                log(f"  - {link}")
        else:
            log("Ссылок не найдено")


def savedata_phone_lookup(phone: str, log: Callable[[str], None] = print) -> None:
    num = str(phone)
    number = num[:-3]
    if not number:
        log("Недостаточно цифр для запроса intelx.")
        return
    pairs = [number[i: i + 2] for i in range(0, len(number), 2)]
    num_path = "/".join(pairs)
    url = f"https://data.intelx.io/saverudata/db2/dbpn/{num_path}.csv"
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        log(f"[!] Ошибка запроса к intelx (phone): {exc}")
        return

    if response.status_code != 200:
        log("Ничего не найдено (intelx phone).")
        return

    reader = csv.DictReader(StringIO(response.text))
    rows = list(reader)
    matched_rows = [
        row for row in rows if any(phone.lower() in str(v).lower() for v in row.values())
    ]
    if not matched_rows:
        log("Ничего не найдено (intelx phone).")
        return

    log("Найденные строки (intelx phone):")
    for i, row in enumerate(matched_rows, start=1):
        log(f"Запись #{i}")
        for key, value in row.items():
            if value and value.strip():
                log(f"{key}: {value}")
                if key in WHITE_LIST_KEYS:
                    google_search(info_name=value, log=log)
        _log_separator(log)


def savedata_email_lookup(email: str, log: Callable[[str], None] = print) -> None:
    h = hashlib.md5(email.lower().encode()).hexdigest()
    path = f"/saverudata/db2/dbe/{h[0]}/{h[1]}/{h[0:4]}.csv"
    url = f"https://data.intelx.io{path}"
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        log(f"[!] Ошибка запроса к intelx (email): {exc}")
        return

    if response.status_code != 200:
        log("Ничего не найдено (intelx email).")
        return

    reader = csv.DictReader(StringIO(response.text))
    rows = list(reader)
    matched_rows = [
        row for row in rows if any(email.lower() in str(v).lower() for v in row.values())
    ]
    if not matched_rows:
        log("Ничего не найдено (intelx email).")
        return

    log("Найденные строки (intelx email):")
    for i, row in enumerate(matched_rows, start=1):
        log(f"Запись #{i}")
        for key, value in row.items():
            if value and value.strip():
                log(f"{key}: {value}")
                if key in WHITE_LIST_KEYS:
                    google_search(info_name=value, log=log)
        _log_separator(log)


def search_google_account(email: str, log: Callable[[str], None] = print) -> None:
    username = email.split("@")[0]
    url = f"https://gmail-osint.activetk.jp/{username}"
    try:
        response = requests.get(
            url, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        log(f"[!] Ошибка запроса к gmail-osint: {exc}")
        return

    if response.status_code != 200:
        log("Не удалось получить данные профиля Google.")
        return

    soup = BeautifulSoup(response.text, "html.parser")
    result_div = soup.find(
        "div",
        style="margin:16px auto;text-align:center;display:block;border:1px solid #000;",
    )
    if not result_div:
        log(response.text)
        return

    content = ""
    for element in result_div.descendants:
        if element.name == "pre":
            continue
        if element.string:
            content += element.string.strip() + "\n"
    lines = content.split("\n")
    formatted_content = ["Google Account data"]
    for idx, line in enumerate(lines):
        if "Custom profile picture" in line and idx + 1 < len(lines):
            formatted_content.append(
                f"Custom profile picture: {lines[idx + 1]}")
        elif "Last profile edit" in line:
            formatted_content.append(
                f"Last profile edit: {line.split(': ')[1]}")
        elif "Email" in line and idx + 1 < len(lines):
            formatted_content.append(f"Email: {lines[idx + 1]}")
        elif "Gaia ID" in line:
            formatted_content.append(f"Gaia ID: {line.split(': ')[1]}")
        elif "User types" in line and idx + 1 < len(lines):
            formatted_content.append(f"User types: {lines[idx + 1]}")
        elif "Profile page" in line and idx + 1 < len(lines):
            formatted_content.append(
                f"Google Maps Profile page: {lines[idx + 1]}")
        elif "No public Google Calendar" in line:
            formatted_content.append("No public Google Calendar.")
    for line in formatted_content:
        log(line)


def telegram_profile(username: str, log: Callable[[str], None] = print) -> None:
    url = f"https://t.me/{username}"
    try:
        response = requests.get(
            url, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        log(f"[!] Ошибка запроса Telegram: {exc}")
        return

    if response.status_code != 200:
        log("Аккаунт Telegram не найден.")
        return

    soup = BeautifulSoup(response.text, "html.parser")
    name_span = soup.find("span", dir="auto")
    description_div = soup.find("div", class_="tgme_page_description")
    if name_span:
        log(f"Имя: {name_span.text}")
        google_search(info_name=name_span.text, log=log)
    if description_div:
        log(f"Описание: {description_div.text}")


def search_username(username: str, log: Callable[[str], None] = print) -> None:
    urls = [
        f"https://www.roblox.com/user.aspx?username={username}",
        f"https://gitlab.com/{username}",
        f"https://pypi.org/user/{username}/",
        f"https://www.instagram.com/{username}",
        f"https://www.twitch.tv/{username}",
        f"https://www.facebook.com/{username}",
        f"https://www.twitter.com/{username}",
        f"https://www.youtube.com/@{username}",
        f"https://plus.google.com/s/{username}/top",
        f"https://imgur.com/user/{username}",
        f"https://open.spotify.com/user/{username}",
        f"https://www.dailymotion.com/{username}",
        f"https://keybase.io/{username}",
        f"https://pastebin.com/u/{username}",
        f"https://www.wikipedia.org/wiki/User:{username}",
        f"https://news.ycombinator.com/user?id={username}",
        f"https://trello.com/{username}",
        f"https://about.me/{username}",
        f"https://www.slideshare.net/{username}",
        f"https://www.last.fm/user/{username}",
        f"https://dribbble.com/{username}",
        f"https://foursquare.com/{username}",
        f"https://www.trip.skyscanner.com/user/{username}",
        f"https://www.zillow.com/profile/{username}",
        f"https://www.meetup.com/members/{username}",
        f"https://www.patreon.com/{username}",
        f"https://www.buzzfeed.com/{username}",
        f"https://www.mixcloud.com/{username}",
        f"https://www.etsy.com/people/{username}",
        f"https://www.tiktok.com/{username}",
    ]
    for url in urls:
        try:
            response = requests.get(
                url, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT)
        except requests.RequestException:
            log(f"{url} - не отвечает")
            continue
        if response.status_code == 200:
            log(f"Аккаунт найден: {url}")


def _normalize_phone(raw_phone: str) -> str:
    digits = re.sub(r"[^\d]", "", raw_phone)
    return digits


def _render_banner(log: Callable[[str], None]) -> None:
    banner = (
        " _          _ _                    ____                      _     \n"
        "| |    __ _(_) |_ _____  ____  __ / ___|  ___  __ _ _ __ ___| |__  \n"
        "| |   / _` | | __/ _ \\ \\/ /\\ \\/ / \\___ \\ / _ \\/ _` | '__/ __| '_ \\ \n"
        "| |__| (_| | | || (_) >  <  >  <   ___) |  __/ (_| | | | (__| | | |\n"
        "|_____\\__,_|_|\\__\\___/_/\\_\\/_/\\_\\ |____/ \\___|\\__,_|_|  \\___|_| |_|\n"
        "By Zenith\n"
    )
    log(banner)


def _phone_search_flow(phone: str, log: Callable[[str], None]) -> None:
    clean_phone = _normalize_phone(phone)
    if not clean_phone:
        log("Телефон не указан.")
        return

    _log_separator(log)
    log(f"Поиск по номеру: {clean_phone}")
    _log_separator(log)
    phone_number_lookup(clean_phone, log=log)
    _log_separator(log)
    ok_response = check_login(clean_phone, log=log)
    console_output(ok_response, log=log)
    _log_separator(log)
    google_search_phone(clean_phone, log=log)
    _log_separator(log)
    savedata_phone_lookup(clean_phone, log=log)
    _log_separator(log)
    results = fetch_data(clean_phone)
    formatted = format_results(results)
    if formatted:
        log("Результаты поиска (comb/proxynova):")
        log(formatted)
    else:
        log("К сожалению, ничего не найдено.")


def _email_search_flow(email: str, log: Callable[[str], None]) -> None:
    email = email.strip()
    if not email:
        log("Email не указан.")
        return

    _log_separator(log)
    log(f"Поиск по email: {email}")
    _log_separator(log)
    savedata_email_lookup(email, log=log)
    _log_separator(log)
    search_google_account(email, log=log)
    _log_separator(log)
    results = fetch_data(email)
    formatted = format_results(results)
    if formatted:
        log("Результаты поиска (comb/proxynova):")
        log(formatted)
    else:
        log("К сожалению, ничего не найдено.")


def _telegram_search_flow(username: str, log: Callable[[str], None]) -> None:
    username = username.strip().lstrip("@")
    if not username:
        log("Username не указан.")
        return

    _log_separator(log)
    log(f"Поиск Telegram: {username}")
    _log_separator(log)
    telegram_profile(username, log=log)
    _log_separator(log)
    search_username(username, log=log)


def _interactive_prompt(log: Callable[[str], None]) -> tuple[str | None, str | None]:
    _render_banner(log)
    log("")
    log(f"1) {Color.GREEN}Поиск по номеру{Color.RESET}")
    log(f"2) {Color.GREEN}Поиск по email{Color.RESET}")
    log(f"3) {Color.GREEN}Поиск по Telegram{Color.RESET}")

    choice = input(
        f"{Color.DARK_RED}Выберите опцию (1-3): {Color.RESET}").strip()
    mode_map = {"1": "phone", "2": "email", "3": "telegram"}
    mode = mode_map.get(choice)
    if not mode:
        log("Неизвестный выбор.")
        return None, None

    prompt_map = {
        "phone": "Введите номер телефона (без +): ",
        "email": "Введите email: ",
        "telegram": "Введите Telegram username: ",
    }
    value = input(prompt_map[mode]).strip()
    return mode, value


def data_search_tool(input_data: dict[str, str] | None = None) -> None:
    log = print
    if isinstance(input_data, dict):
        mode = input_data.get("mode")
        value = (input_data.get("value") or "").strip()
    else:
        mode, value = _interactive_prompt(log)

    if not mode or not value:
        log("Недостаточно данных для поиска.")
        return

    if mode == "phone":
        _phone_search_flow(value, log)
    elif mode == "email":
        _email_search_flow(value, log)
    elif mode == "telegram":
        _telegram_search_flow(value, log)
    else:
        log(f"Неизвестный тип поиска: {mode}")
