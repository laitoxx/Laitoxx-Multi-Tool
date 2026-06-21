import subprocess

from laitoxx.features.utilities.shared_utils import Color


def port_scanner_tool():
    """
    Launch zenmap GUI for port scanning instead of programmatic nmap.
    """
    import platform
    import shutil

    try:
        zenmap_cmd = shutil.which("zenmap")
        if zenmap_cmd:
            subprocess.Popen([zenmap_cmd])
            print("Zenmap launched successfully.")
        else:
            if platform.system() == "Windows":
                subprocess.Popen(
                    [
                        r"C:\Program Files (x86)\Nmap\zenmap\bin\pythonw.exe",
                        "-c",
                        "from zenmapGUI.App import run;run()",
                    ]
                )
                print("Zenmap launched successfully.")
            else:
                raise FileNotFoundError
    except FileNotFoundError:
        print(
            f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Zenmap Error: Zenmap not found at the specified path."
        )
        print(
            f"{Color.DARK_GRAY}[{Color.CYAN}ℹ{Color.DARK_GRAY}]{Color.CYAN} Note: Zenmap is not a pip package. You can download it from: https://nmap.org/download"
        )
    except Exception as e:
        print(
            f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} An unexpected error occurred: {e}"
        )
