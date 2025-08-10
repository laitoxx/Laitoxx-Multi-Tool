import requests
from bs4 import BeautifulSoup
from ..shared_utils import Color

def gmail_osint():
    """
    Performs an OSINT search on a Gmail address using the activetk.jp service.
    """
    email_prefix = input(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Enter the email prefix (e.g., for 'example@gmail.com', enter 'example'): {Color.RESET}"
    )
    if email_prefix is None:
        return
    email_prefix = email_prefix.strip()

    if not email_prefix:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} No email prefix entered.")
        return

    url = f"https://gmail-osint.activetk.jp/{email_prefix}"
    print(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Searching for Google profile at {url}...")

    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Find the main result container
        result_div = soup.find('div', style=lambda value: 'border:1px solid #000' in value if value else False)

        if not result_div or "Not Found" in result_div.text:
            print(f"\n{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} No Google account found for prefix '{email_prefix}'.")
            return

        print(f"\n{Color.DARK_GRAY}[{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Google Account Data Found:")

        # Extract and print data in a structured way
        data = {}
        all_text = result_div.get_text(separator='\n', strip=True)
        lines = all_text.split('\n')

        # Simple key-value extraction
        data_map = {
            "Gaia ID": "Gaia ID",
            "Email": "Email",
            "Last profile edit": "Last profile edit",
            "Custom profile picture": "Custom profile picture",
            "User types": "User types"
        }

        for i, line in enumerate(lines):
            for key, keyword in data_map.items():
                if keyword in line and i + 1 < len(lines):
                    value = lines[i + 1]
                    if "http" in value: # It's a link
                        data[key] = value
                    else: # It's regular text
                        data[key] = line.split(':')[-1].strip() if ':' in line else value

        # Handling for profile page and calendar is a bit different
        profile_page = result_div.find('a', href=lambda href: href and "maps.google.com" in href)
        if profile_page:
            data["Google Maps Profile"] = profile_page['href']

        if "No public Google Calendar" in all_text:
            data["Google Calendar"] = "No public calendar found"
        else:
            calendar_link = result_div.find('a', href=lambda href: href and "calendar.google.com" in href)
            if calendar_link:
                data["Google Calendar"] = calendar_link['href']

        # Print the extracted data
        for label, value in data.items():
            print(f"  {Color.DARK_GRAY}-{Color.WHITE} {label:<22}: {Color.LIGHT_BLUE}{value}")

    except requests.exceptions.Timeout:
        print(f"\n{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} The request timed out. The service might be down.")
    except requests.exceptions.RequestException as e:
        print(f"\n{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} An error occurred: {e}")
