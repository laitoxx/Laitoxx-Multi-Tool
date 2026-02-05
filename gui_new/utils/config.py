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

import json
import os
from pathlib import Path


def save(filepath: Path, value: str) -> bool:
    with open(filepath, "w") as file:
        file.write(value)

    return True


def load(filepath: Path) -> str | bool:
    if os.path.exists(filepath):
        with open(filepath) as file:
            return file.read().strip()

    return False


def load_theme(filepath: Path) -> dict | bool:
    try:
        if os.path.exists(filepath):
            with open(filepath) as file:
                return json.load(file)
    except (json.JSONDecodeError, OSError):
        return False
    return False


def save_theme(filepath: Path, data: dict) -> bool:
    with open(filepath, "w") as file:
        json.dump(data, file, indent=4)

    return True
