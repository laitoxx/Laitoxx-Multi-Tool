import requests
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from ..shared_utils import Color
import random
import string

def get_domains():
    """
    Fetches the list of available domains from 1secmail.
    """
    try:
        response = requests.get("https://www.1secmail.com/api/v1/?action=getDomainList")
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError):
        return ["1secmail.com", "1secmail.org", "1secmail.net"] # Fallback domains

def get_mailbox_messages(login, domain):
    """
    Fetches messages from the mailbox.
    """
    try:
        url = f'https://www.1secmail.com/api/v1/?action=getMessages&login={login}&domain={domain}'
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError):
        return []

def get_message_details(login, domain, message_id):
    """
    Fetches the full details of a single message.
    """
    try:
        url = f'https://www.1secmail.com/api/v1/?action=readMessage&login={login}&domain={domain}&id={message_id}'
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError):
        return None

def temp_mail():
    """
    Creates a temporary email address and monitors its inbox for new messages.
    """
    print(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_BLUE} Temporary Email Generator (1secmail.com)")

    # Create email address
    local_part = input(f"{Color.DARK_GRAY}  - {Color.WHITE}Enter a username for your email [random]: {Color.RESET}")
    if local_part is None:
        return
    local_part = local_part.strip()
    if not local_part:
        local_part = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))

    available_domains = get_domains()
    domain = random.choice(available_domains)
    email = f"{local_part}@{domain}"

    print(f"\n{Color.DARK_GRAY}[{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Your temporary email is: {Color.WHITE}{email}")
    print(f"{Color.GRAY}Checking for new messages every 5 seconds. Press Ctrl+C to exit.")

    processed_message_ids = set()
    try:
        while True:
            messages = get_mailbox_messages(local_part, domain)

            if messages:
                for message in messages:
                    msg_id = message['id']
                    if msg_id not in processed_message_ids:
                        details = get_message_details(local_part, domain, msg_id)
                        if details:
                            # Adjust time to be more readable
                            date_obj = datetime.strptime(details["date"], "%Y-%m-%d %H:%M:%S")
                            adjusted_time = (date_obj + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S")

                            print(f"\n{Color.DARK_RED}┌─[ {Color.LIGHT_RED}New Message Received! {Color.DARK_RED}]─")
                            print(f"{Color.DARK_RED}│ {Color.LIGHT_RED}{'From':<8}: {Color.WHITE}{details['from']}")
                            print(f"{Color.DARK_RED}│ {Color.LIGHT_RED}{'Subject':<8}: {Color.WHITE}{details['subject']}")
                            print(f"{Color.DARK_RED}│ {Color.LIGHT_RED}{'Date':<8}: {Color.WHITE}{adjusted_time}")
                            print(f"{Color.DARK_RED}├─[ {Color.LIGHT_RED}Body {Color.DARK_RED}]─")

                            # Clean up body text
                            soup = BeautifulSoup(details.get("body", ""), 'html.parser')
                            body_text = soup.get_text(separator='\n', strip=True)
                            for line in body_text.split('\n'):
                                print(f"{Color.DARK_RED}│ {Color.GRAY}{line}")

                            print(f"{Color.DARK_RED}└" + '─' * 30)

                            processed_message_ids.add(msg_id)

            time.sleep(5)

    except KeyboardInterrupt:
        print(f"\n\n{Color.DARK_RED}Stopping email checker. Returning to main menu...{Color.RESET}")
    except Exception as e:
        print(f"\n{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} An unexpected error occurred: {e}")
