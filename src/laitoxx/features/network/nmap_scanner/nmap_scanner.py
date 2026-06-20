import subprocess


def nmap_scanner_tool():
    """
    Launch zenmap GUI/Nmap for scanning instead of programmatic nmap.
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

            elif platform.system() == "Linux":
                nmap_cmd = shutil.which("nmap")
                if nmap_cmd:
                    print("Zenmap not found. Falling back to Nmap CLI.")
                    print("Please enter the target manually in the terminal window that opens.")
                    print("Example: nmap -F scanme.nmap.org")

                    subprocess.Popen([
                    "xterm",
                    "-e",
                    "bash",
                    "-c",
                    "echo 'Enter your Nmap command manually.'; exec bash"
                 ])
                else:
                    raise FileNotFoundError
    except FileNotFoundError:
        print("Zenmap Error: Zenmap not found at the specified path.")
        print(
            "Note: Zenmap is not a pip package. You can download it from: https://nmap.org/download"
        )
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    nmap_scanner_tool()
