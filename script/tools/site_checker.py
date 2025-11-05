import requests
import time
from urllib.parse import urlparse
from ..shared_utils import Color

def check_site():
    """
    Checks the availability and status of a website.
    """
    url = input(f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Enter website URL (e.g., https://example.com): {Color.RESET}").strip()

    if not url:
        print(f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.RED} No URL entered.")
        return

    # Prepend http:// if no scheme is present
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url

    parsed_url = urlparse(url)
    if not parsed_url.netloc:
        print(f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.RED} Invalid URL format.")
        return

    print(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Checking availability for {url}...")

    try:
        start_time = time.time()
        response = requests.get(url, timeout=10, allow_redirects=True)
        end_time = time.time()

        response_time = (end_time - start_time) * 1000  # in milliseconds

        status_code = response.status_code

        if 200 <= status_code < 300:
            status_color = Color.LIGHT_GREEN
            status_text = "is available!"
        elif 400 <= status_code < 500:
            status_color = Color.YELLOW
            status_text = "is not available (Client Error)."
        elif 500 <= status_code < 600:
            status_color = Color.RED
            status_text = "is not available (Server Error)."
        else:
            status_color = Color.GRAY
            status_text = "has an unusual status."

        print(f"\n{Color.DARK_GRAY}[{status_color}✔{Color.DARK_GRAY}]{status_color} Website {status_text}")
        print(f"{Color.DARK_GRAY}  - {Color.WHITE}Status Code: {status_color}{status_code}")
        print(f"{Color.DARK_GRAY}  - {Color.WHITE}Response Time: {Color.LIGHT_BLUE}{response_time:.2f} ms")

        server = response.headers.get('Server')
        if server:
            print(f"{Color.DARK_GRAY}  - {Color.WHITE}Server: {Color.LIGHT_PURPLE}{server}")

        if response.history:
            print(f"{Color.DARK_GRAY}  - {Color.WHITE}Redirects followed: {Color.GRAY}{len(response.history)}")
            print(f"{Color.DARK_GRAY}  - {Color.WHITE}Final URL: {Color.GRAY}{response.url}")

    except requests.exceptions.RequestException as e:
        print(f"\n{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Error checking website: {e}")
