#!/usr/bin/env bash
echo "========================================"
echo "Laitoxx Linux/macOS Installer"
echo "========================================"

echo "Checking for a compatible Python version (>= 3.10 and <= 3.13)..."
VALID_PYTHON=""

for py in python3.13 python3.12 python3.11 python3.10 python3 python; do
    if command -v $py >/dev/null 2>&1; then
        IS_VALID=$($py -c 'import sys; print("1" if (sys.version_info.major == 3 and 10 <= sys.version_info.minor <= 13) else "0")')
        if [ "$IS_VALID" = "1" ]; then
            VALID_PYTHON=$py
            echo "Found valid Python: $($py --version)"
            break
        fi
    fi
done

if [ -z "$VALID_PYTHON" ]; then
    echo "Compatible Python not found. Python 3.14+ is known to cause issues with PyQt6 and dependencies at startup."
    echo "Attempting to install Python 3.13 automatically..."
    
    if command -v apt-get >/dev/null 2>&1; then
        echo "Detected Debian/Ubuntu-based system. Installing via apt..."
        sudo apt-get update
        sudo apt-get install -y software-properties-common
        sudo add-apt-repository -y ppa:deadsnakes/ppa
        sudo apt-get update
        sudo apt-get install -y python3.13 python3.13-venv python3.13-dev
        VALID_PYTHON="python3.13"
    elif command -v dnf >/dev/null 2>&1; then
        echo "Detected Fedora/RHEL-based system. Installing via dnf..."
        sudo dnf install -y python3.13
        VALID_PYTHON="python3.13"
    elif command -v pacman >/dev/null 2>&1; then
        echo "Detected Arch-based system. Installing via pacman..."
        echo "Note: Arch uses the latest Python by default. We will try to install it but if it's 3.14+, you may need to use AUR (e.g. yay -S python313)."
        sudo pacman -Sy --noconfirm python
        VALID_PYTHON="python3"
    elif command -v brew >/dev/null 2>&1; then
        echo "Detected macOS/Homebrew. Installing via brew..."
        brew install python@3.13
        VALID_PYTHON="python3.13"
    else
        echo "Could not determine package manager. Please install Python 3.13 manually."
        exit 1
    fi
    
    if ! command -v $VALID_PYTHON >/dev/null 2>&1; then
        echo "Automatic installation failed or $VALID_PYTHON not found in PATH."
        exit 1
    fi
    
    IS_VALID=$($VALID_PYTHON -c 'import sys; print("1" if (sys.version_info.major == 3 and 10 <= sys.version_info.minor <= 13) else "0")')
    if [ "$IS_VALID" != "1" ]; then
        echo "Installed Python version is still not compatible (likely 3.14+). Please install Python 3.13 manually."
        exit 1
    fi
fi

echo "Creating virtual environment in 'venv' folder..."
$VALID_PYTHON -m venv venv
if [ $? -ne 0 ]; then
    echo "Failed to create virtual environment. Ensure the python3-venv package is installed."
    echo "Example: sudo apt-get install python3.13-venv"
    exit 1
fi

echo "Activating virtual environment and installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "Downloading vis-network for local rendering..."
python acquire_vis_network.py

echo ""
echo "========================================"
echo "Installation complete!"
echo "Run 'python3 start.py' to launch Laitoxx."
echo "========================================"
