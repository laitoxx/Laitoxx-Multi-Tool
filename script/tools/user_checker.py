import requests
import concurrent.futures
import threading
from ..shared_utils import Color

_NEGATIVE_PATTERNS = [
    "not found", "does not exist", "page not found", "no results",
    "user not found", "profile not found", "account not found",
    "sorry, this page", "content unavailable",
]

_TLS = threading.local()


def _make_session():
    try:
        from settings.proxy import make_session
        from settings.app_settings import settings as _app_settings
        return make_session(_app_settings.proxy)
    except Exception:
        return requests.Session()


def _get_session():
    if not hasattr(_TLS, "session"):
        _TLS.session = _make_session()
        _TLS.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        })
    return _TLS.session


def check_platform(platform, url_template, username):
    url = url_template.format(username=username)
    try:
        session = _get_session()
        response = session.get(url, timeout=10, allow_redirects=True)
        if response.status_code == 200:
            text_lower = response.text.lower()
            username_lower = username.lower()
            if any(p in text_lower for p in _NEGATIVE_PATTERNS):
                return None, None
            if username_lower in response.url.lower() or username_lower in text_lower:
                return platform, url
    except requests.RequestException:
        pass
    return None, None


def check_username():
    urls = {
        "Twitter": "https://twitter.com/{username}",
        "Instagram": "https://www.instagram.com/{username}",
        "Facebook": "https://www.facebook.com/{username}",
        "Telegram": "https://t.me/{username}",
        "YouTube": "https://www.youtube.com/@{username}",
        "Reddit": "https://www.reddit.com/user/{username}",
        "Roblox": "https://www.roblox.com/users/profile?username={username}",
        "VKontakte": "https://vk.com/{username}",
        "TikTok": "https://www.tiktok.com/@{username}",
        "Pinterest": "https://www.pinterest.com/{username}",
        "GitHub": "https://github.com/{username}",
        "Twitch": "https://www.twitch.tv/{username}",
        "LinkedIn": "https://www.linkedin.com/in/{username}",
        "Snapchat": "https://www.snapchat.com/add/{username}",
        "Flickr": "https://flickr.com/people/{username}",
        "Vimeo": "https://vimeo.com/{username}",
        "SoundCloud": "https://soundcloud.com/{username}",
        "Medium": "https://medium.com/@{username}",
        "Patreon": "https://www.patreon.com/{username}",
        "Spotify": "https://open.spotify.com/user/{username}",
        "Steam": "https://steamcommunity.com/id/{username}",
        "Tumblr": "https://{username}.tumblr.com/",
        "WordPress": "https://{username}.wordpress.com/",
        "DeviantArt": "https://{username}.deviantart.com/",
        "Pastebin": "https://pastebin.com/u/{username}",
        "Keybase": "https://keybase.io/{username}",
        "Dribbble": "https://dribbble.com/{username}",
        "Behance": "https://www.behance.net/{username}",
        "Bandcamp": "https://bandcamp.com/{username}",
    }

    username = input(f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Enter a username to check: {Color.RESET}").strip()
    if not username:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Username cannot be empty.")
        return

    print(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Checking for username '{username}' on {len(urls)} platforms...")

    found_accounts = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        future_to_platform = {
            executor.submit(check_platform, platform, url_template, username): platform
            for platform, url_template in urls.items()
        }

        for i, future in enumerate(concurrent.futures.as_completed(future_to_platform)):
            platform, url = future.result()
            if platform and url:
                found_accounts[platform] = url

            print(f"\r{Color.DARK_GRAY}Progress: {i+1}/{len(urls)} platforms checked... Found: {len(found_accounts)}", end="")

    print("\n")
    if not found_accounts:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} No accounts found for username '{username}' on these platforms.")
    else:
        print(f"{Color.DARK_GRAY}[{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Found {len(found_accounts)} account(s):")
        for platform, url in sorted(found_accounts.items()):
            print(f"  {Color.DARK_GRAY}-{Color.WHITE} {platform:<15}: {Color.LIGHT_BLUE}{url}")
