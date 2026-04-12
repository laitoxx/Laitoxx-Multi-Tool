import subprocess

def nmap_scanner_tool():
    """
    Launch zenmap GUI for scanning instead of programmatic nmap.
    """
    try:
        subprocess.Popen([r"C:\Program Files (x86)\Nmap\zenmap\bin\pythonw.exe", "-c", "from zenmapGUI.App import run;run()"])
        print("Zenmap launched successfully.")
    except FileNotFoundError:
        print("Zenmap Error: Zenmap not found at the specified path.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    nmap_scanner_tool()
