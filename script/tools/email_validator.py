import re
from ..shared_utils import Color

def is_valid_email(email: str) -> bool:
    """Returns True if the email address passes a standard regex check."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def check_email_address():
    """
    Tool function to get user input and validate an email address.
    """
    email = input(f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}Enter email address: {Color.RESET}")
    if email is None:
        return
    email = email.strip()

    if not email:
        print(f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.RED}No email address entered.{Color.RESET}")
        return

    if is_valid_email(email):
        print(
            f"{Color.DARK_GRAY}[{Color.LIGHT_GREEN}✔{Color.DARK_GRAY}]"
            f"{Color.LIGHT_GREEN} Format OK for '{email}'. (Syntax only){Color.RESET}"
        )
    else:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Email address '{email}' is invalid.{Color.RESET}")
