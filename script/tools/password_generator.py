"""
 @@@  @@@  @@@@@@  @@@@@@@ @@@@@@@  @@@@@@@  @@@ @@@@@@@@ @@@ @@@
 @@!  @@@ @@!  @@@   @@!   @@!  @@@ @@!  @@@ @@! @@!      @@! !@@
 @!@!@!@! @!@  !@!   @!!   @!@  !@! @!@!!@!  !!@ @!!!:!    !@!@! 
 !!:  !!! !!:  !!!   !!:   !!:  !!! !!: :!!  !!: !!:        !!:  
  :   : :  : :. :     :    :: :  :   :   : : :    :         .:   
                                                                 
    HOTDRIFY cooked with the refactor for the LAITOXX squad.
                    github.com/hotdrify
                      t.me/hotdrify

                    github.com/laitoxx
                      t.me/laitoxx
"""

import random
import string
from typing import List, LiteralString

from ..shared_utils import Color


def get_characters(complexity: str) -> LiteralString:
    if complexity == "low":
        return string.ascii_letters + string.digits
    elif complexity == "medium":
        return string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    elif complexity == "high":
        return string.ascii_letters + string.digits + string.punctuation
    else:
        return string.ascii_letters + string.digits


def password_generator_tool() -> None:
    args: str = input(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED}Enter password length and complexity (e.g., 12 medium) -> {Color.RESET}")
    if args is None:
        return
    args: str = args.strip()
    if args:
        parts: list[str] = args.split()
        if not parts:
            password_length: int = 12
            complexity: str = "medium"
        else:
            try:
                password_length: int = int(parts[0])
                if password_length <= 0:
                    print(
                        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.RED}Password length must be a positive number.{Color.RESET}")
                    return
            except ValueError:
                print(
                    f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.RED}Invalid input. Please enter a valid number for the length.{Color.RESET}")
                return
            complexity: str = parts[1] if len(parts) > 1 else "medium"
    else:
        password_length: int = 12
        complexity: str = "medium"

    complexity: str = complexity.lower()
    if complexity not in ["low", "medium", "high"]:
        complexity: str = "medium"

    characters: LiteralString = get_characters(complexity)
    password: str = "".join(random.choice(characters)
                            for _ in range(password_length))

    print(
        f"\n{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_GREEN}Generated Password: {Color.WHITE}{password}{Color.RESET}")
