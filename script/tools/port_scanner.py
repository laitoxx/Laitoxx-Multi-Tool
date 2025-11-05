import subprocess
from ..shared_utils import Color

def port_scanner_tool():
    """
    Launch zenmap GUI for port scanning instead of programmatic nmap.
    """
    try:
        subprocess.Popen([r"C:\Program Files (x86)\Nmap\zenmap\bin\pythonw.exe", "-c", "from zenmapGUI.App import run;run()"])
        print("Zenmap launched successfully.")
    except FileNotFoundError:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} Zenmap Error: Zenmap not found at the specified path.")
    except Exception as e:
        print(f"{Color.DARK_GRAY}[{Color.RED}✖{Color.DARK_GRAY}]{Color.RED} An unexpected error occurred: {e}")
