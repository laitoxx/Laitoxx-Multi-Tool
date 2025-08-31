import requests
import concurrent.futures
from ..shared_utils import Color

def check_platform(session, platform, url_template, username):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    url = url_template.format(username=username)
    try:
        response = session.get(url, headers=headers, timeout=10, allow_redirects=True)
        if response.status_code == 200 and username.lower() in response.url.lower():
            return platform, url
        if response.status_code == 200 and not response.history:
            if "not found" not in response.text.lower() and "does not exist" not in response.text.lower():
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
        with requests.Session() as session:
            future_to_platform = {
                executor.submit(check_platform, session, platform, url_template, username): platform
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