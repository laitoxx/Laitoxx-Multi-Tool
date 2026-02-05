import requests

from ..shared_utils import Color


def check_url():
    url = input(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Enter the URL to check for redirects: {Color.RESET}")
    try:
        response = requests.get(url, timeout=10, allow_redirects=True)
        response.raise_for_status()

        if response.history:
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} URL has redirects:")
            for i, resp in enumerate(response.history):
                print(
                    f"{Color.DARK_GRAY}  [{i+1}] {resp.status_code} -> {resp.url}")
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Final destination: {response.status_code} -> {response.url}")
        else:
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_GREEN} No redirects. URL is direct.")

    except requests.exceptions.HTTPError as e:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} HTTP Error checking URL {url}: {e}")
    except requests.exceptions.ConnectionError as e:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Connection Error checking URL {url}: {e}")
    except requests.exceptions.Timeout as e:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Timeout checking URL {url}: {e}")
    except requests.exceptions.RequestException as e:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Error checking URL {url}: {e}")
