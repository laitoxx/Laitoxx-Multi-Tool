"""Shared terminal colours for tool output captured by the GUI."""

from colorama import Fore, init

init(autoreset=True)


class Color:
    DARK_RED = Fore.RED
    DARK_GRAY = Fore.LIGHTBLACK_EX
    WHITE = Fore.WHITE
    RESET = Fore.RESET
    LIGHT_RED = Fore.LIGHTRED_EX
    RED = Fore.RED
    GRAY = Fore.LIGHTWHITE_EX
    LIGHT_GREEN = Fore.LIGHTGREEN_EX
    GREEN = Fore.GREEN
    DARK_GREEN = Fore.GREEN
    LIGHT_PURPLE = Fore.LIGHTMAGENTA_EX
    PURPLE = Fore.MAGENTA
    DARK_PURPLE = Fore.MAGENTA
    LIGHT_BLUE = Fore.LIGHTBLUE_EX
    BLUE = Fore.BLUE
    DARK_BLUE = Fore.BLUE
    YELLOW = Fore.YELLOW
    CYAN = Fore.CYAN
