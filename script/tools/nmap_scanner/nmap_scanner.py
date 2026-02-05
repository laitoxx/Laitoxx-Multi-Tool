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

import subprocess
from pathlib import Path


def nmap_scanner_tool():
    # edit your nmap path, pls
    NMAP_PATH: Path = Path(
        r"C:\Program Files (x86)\Nmap\zenmap\bin\pythonw.exe")

    try:
        subprocess.Popen(
            [NMAP_PATH, "-c", "from zenmapGUI.App import run;run()"])
        print("Zenmap launched successfully.")
    except FileNotFoundError:
        print("Zenmap Error: Zenmap not found at the specified path.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    nmap_scanner_tool()
