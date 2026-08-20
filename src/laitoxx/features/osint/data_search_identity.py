from collections.abc import Callable

import requests
from bs4 import BeautifulSoup

from .data_search_common import _log_separator, fetch_data, format_results, log_savedata_result
from .savedata_client import SaveDataClient

REQUEST_TIMEOUT = 10

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/119.0 Safari/537.36"
}


def savedata_email_lookup(
    email: str,
    log: Callable[[str], None] = print,
    *,
    enrich: bool = False,
) -> None:
    result = SaveDataClient().lookup_email(email)
    log_savedata_result(result, "SaveRuData email", log, enrich=enrich)


def search_google_account(email: str, log: Callable[[str], None] = print) -> None:
    domain = email.rsplit("@", 1)[-1].casefold()
    if domain not in {"gmail.com", "googlemail.com"}:
        log("Google profile lookup skipped: the address is not hosted by Gmail.")
        return
    username = email.split("@")[0]
    url = f"https://gmail-osint.activetk.jp/{username}"
    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        log(f"[!] gmail-osint request error: {exc}")
        return

    if response.status_code != 200:
        log("Failed to retrieve Google profile data.")
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
            formatted_content.append(f"Custom profile picture: {lines[idx + 1]}")
        elif "Last profile edit" in line:
            formatted_content.append(f"Last profile edit: {line.split(': ')[1]}")
        elif "Email" in line and idx + 1 < len(lines):
            formatted_content.append(f"Email: {lines[idx + 1]}")
        elif "Gaia ID" in line:
            formatted_content.append(f"Gaia ID: {line.split(': ')[1]}")
        elif "User types" in line and idx + 1 < len(lines):
            formatted_content.append(f"User types: {lines[idx + 1]}")
        elif "Profile page" in line and idx + 1 < len(lines):
            formatted_content.append(f"Google Maps Profile page: {lines[idx + 1]}")
        elif "No public Google Calendar" in line:
            formatted_content.append("No public Google Calendar.")
    for line in formatted_content:
        log(line)


def _email_search_flow(
    email: str,
    log: Callable[[str], None],
    *,
    enrich_savedata: bool = False,
) -> None:
    email = email.strip()
    if not email:
        log("Email not provided.")
        return

    _log_separator(log)
    log(f"Searching by email: {email}")
    _log_separator(log)
    savedata_email_lookup(email, log=log, enrich=enrich_savedata)
    _log_separator(log)
    search_google_account(email, log=log)
    _log_separator(log)
    results = fetch_data(email)
    formatted = format_results(results)
    if formatted:
        log("Results (comb/proxynova):")
        log(formatted)
    else:
        log("Nothing found.")
