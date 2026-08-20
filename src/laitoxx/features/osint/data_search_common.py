from collections.abc import Callable, Sequence

import requests
from bs4 import BeautifulSoup

from .savedata_client import ENRICHMENT_KEYS, SaveDataResult

OK_LOGIN_URL = "https://www.ok.ru/dk?st.cmd=anonymMain&st.accRecovery=on&st.error=errors.password.wrong"
OK_RECOVER_URL = "https://www.ok.ru/dk?st.cmd=anonymRecoveryAfterFailedLogin&st._aid=LeftColumn_Login_ForgotPassword"

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


def log_savedata_result(
    result: SaveDataResult,
    label: str,
    log: Callable[[str], None] = print,
    *,
    enrich: bool = False,
) -> None:
    if result.error:
        log(f"[!] {result.error}")
        return
    if not result.rows:
        log(f"No matches found ({label}).")
        return

    log(f"Found rows ({label}):")
    for match_idx, row in enumerate(result.rows, start=1):
        log(f"Record #{match_idx}")
        for key, value in row.items():
            if not value.strip():
                continue
            log(f"{key}: {value}")
            if enrich and key in ENRICHMENT_KEYS:
                google_search(info_name=value, log=log)
        _log_separator(log)
    if result.truncated:
        log("[!] Result limit reached; more matching rows may be available.")


def _extract_links_from_response(url: str, log: Callable[[str], None]) -> list[str]:
    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        log(f"[!] Request error {url}: {exc}")
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
            return [f"[ERROR] Redirect detected (HTTP {response.status_code})"]
        response.raise_for_status()
        data = response.json()
        return data.get("lines", ["[SORRY] No results."])
    except requests.RequestException as exc:
        return [f"[ERROR] Request error: {exc}"]


def format_results(results: Sequence[str]) -> str:
    formatted_results: list[str] = []
    for item in results:
        if ":" in item:
            email, password = item.split(":", 1)
            formatted_results.append(f"Email: {email.strip()}\nPassword: {password.strip()}")
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
        log(f"Searching: {url}")
        links = _extract_links_from_response(url, log)
        if links:
            for link in links[:10]:
                log(f"  - {link}")
        else:
            log("  No links found")


def check_login(login_data: str, log: Callable[[str], None] = print) -> dict[str, str | None] | None:
    session = requests.Session()
    try:
        session.get(
            f"{OK_LOGIN_URL}&st.email={login_data}",
            headers=DEFAULT_HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        request = session.get(OK_RECOVER_URL, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        log(f"[!] OK.ru request error: {exc}")
        return None

    root_soup = BeautifulSoup(request.content, "html.parser")
    soup = root_soup.find("div", {"data-l": "registrationContainer,offer_contact_rest"})
    if soup:
        account_info = soup.find("div", {"class": "ext-registration_tx taCenter"})
        masked_email = soup.find("button", {"data-l": "t,email"})
        masked_phone = soup.find("button", {"data-l": "t,phone"})

        masked_phone_text = None
        masked_email_text = None
        masked_name = None
        profile_info = None
        profile_registered = None

        if masked_phone:
            masked_phone_text = (masked_phone.find("div", {"class": "ext-registration_stub_small_header"})).get_text()

        if masked_email:
            masked_email_text = (masked_email.find("div", {"class": "ext-registration_stub_small_header"})).get_text()

        if account_info:
            masked_name_tag = account_info.find("div", {"class": "ext-registration_username_header"})
            if masked_name_tag:
                masked_name = masked_name_tag.get_text()

            account_info_divs = account_info.find_all("div", {"class": "lstp-t"})
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
        log("Server returned an unknown response")
        return
    if parsed_response.get("status") == "not associated":
        log("Number is not linked to OK.ru")
        return
    for key, value in parsed_response.items():
        if value:
            log(f"{key.capitalize()}: {value}")
