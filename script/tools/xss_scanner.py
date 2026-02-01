import os
import sys
import requests
import html
from ..shared_utils import Color


def xss_scan():
    """Simple XSS scanner copied from the working old version.

    - Loads payloads from payloads/xsspayloads.txt
    - Tests forms and query-parameter URLs for reflected payloads
    """
    if not os.path.exists('payloads'):
        print(f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Directory with payloads ('payloads') not exist. Please create it and add file with payloads('xsspayloads.txt')")
        return
    xss_payloads_path = os.path.join('payloads', 'xsspayloads.txt')
    if not os.path.isfile(xss_payloads_path):
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} File with payloads not found")
        return
    try:
        with open(xss_payloads_path, 'r', encoding='utf-8') as file:
            payloads = [line.strip() for line in file if line.strip()]
    except Exception as e:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Error reading payloads file: {e}")
        return
    if not payloads:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} No payloads found in the file.")
        return
    print(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Loaded Payloads: {len(payloads)}")
    url = input(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.RED} Enter URL for scan: ")
    entity_conversion = input(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Use entity conversion to HTML? (y/n): ").strip().lower()
    print(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Starting XSS scan on: {url}")
    attempt = 1
    for payload in payloads:
        test_payload = payload
        if entity_conversion == 'y' or entity_conversion == 'Y':
            test_payload = html.escape(payload)
        test_url = f"{url}?q={test_payload}"
        try:
            response = requests.get(test_url, timeout=5)
            if test_payload in response.text:
                sys.stdout.write(
                    f"\rattempt: {attempt} Payload: {payload} status: found Potential XSS vulnerability on {test_url}")
                sys.stdout.flush()
                print(
                    f"\n{Color.DARK_GRAY}[{Color.DARK_RED}{attempt}{Color.DARK_GRAY}]{Color.LIGHT_RED} Potential XSS vulnerability found with payload: {payload} url - {test_url}")
            else:
                sys.stdout.write(
                    f"\rattempt: {attempt} Payload: {payload} status: not found found XSS vulnerability")
                sys.stdout.flush()
                attempt += 1
        except requests.exceptions.RequestException as e:
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Error testing URL: {e}")
    print(
        f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} XSS scan completed.")
