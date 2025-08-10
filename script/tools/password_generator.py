import random
import string
from ..shared_utils import Color

def get_characters(complexity):
    """
    Returns a character set based on the chosen complexity level.
    """
    if complexity == "low":
        return string.ascii_letters + string.digits
    elif complexity == "medium":
        return string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    elif complexity == "high":
        return string.ascii_letters + string.digits + string.punctuation
    else:
        return string.ascii_letters + string.digits

def password_generator_tool():
    """
    Generates a password of a specified length and complexity.
    """
    try:
        length_str = input(f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}Enter password length -> {Color.RESET}")
        if length_str is None:
            return
        password_length = int(length_str)
        if password_length <= 0:
            print(f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.RED}Password length must be a positive number.{Color.RESET}")
            return
    except ValueError:
        print(f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.RED}Invalid input. Please enter a valid number for the length.{Color.RESET}")
        return

    complexity = input(f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}Choose complexity (low, medium, high) [default: medium]: {Color.RESET}")
    if complexity is None:
        return
    complexity = complexity.lower()
    if complexity not in ["low", "medium", "high"]:
        complexity = "medium"

    characters = get_characters(complexity)
    password = "".join(random.choice(characters) for _ in range(password_length))

    print(f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_GREEN}Generated Password: {Color.WHITE}{password}{Color.RESET}")
