import os
import sys
import subprocess

def check_for_updates():
    print("Checking for updates...")
    try:
        # Check if git is available
        subprocess.run(["git", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        
        # Fetch latest changes
        subprocess.run(["git", "fetch"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        
        # Check status
        status_output = subprocess.run(["git", "status", "-uno"], capture_output=True, text=True).stdout
        if "Your branch is behind" in status_output:
            print("\n" + "="*40)
            print("🚀 An update is available for Laitoxx!")
            print("="*40)
            ans = input("Do you want to download and install the update now? (y/n): ")
            if ans.lower() == 'y':
                subprocess.run(["git", "pull"], check=True)
                print("\nUpdate successful! Please note: if dependencies have changed, you may need to re-run install.bat or install.sh.")
                input("Press Enter to continue starting the application...")
            else:
                print("Skipping update.")
        else:
            print("You are up to date.")
    except Exception as e:
        print(f"Update check skipped or failed: {e}")

def main():
    print("Starting Laitoxx-Multi-Tool...")
    check_for_updates()
    
    if os.name == 'nt':
        python_executable = os.path.join("venv", "Scripts", "python.exe")
    else:
        python_executable = os.path.join("venv", "bin", "python")
        
    if not os.path.exists(python_executable):
        print(f"\n❌ Virtual environment not found at {python_executable}.")
        print("Please run 'install.bat' (Windows) or 'install.sh' (Linux/macOS) first to setup the environment.")
        sys.exit(1)
        
    print(f"Launching using virtual environment: {python_executable}\n")
    try:
        # We use subprocess.call to wait for the GUI to finish
        sys.exit(subprocess.call([python_executable, "gui.py"] + sys.argv[1:]))
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)

if __name__ == "__main__":
    main()
