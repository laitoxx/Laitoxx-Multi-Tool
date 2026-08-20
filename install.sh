#!/usr/bin/env bash
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

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
if ! python -m pip install --upgrade pip; then
    echo "[WARNING] pip could not be upgraded; continuing with the bundled version."
fi
if ! python -m pip install -r requirements.txt; then
    echo "[ERROR] Python dependencies could not be installed from requirements.txt."
    echo "Check the pip error above (network/TLS, unsupported Python wheel, compiler, or system headers), then retry."
    exit 1
fi

INSTALL_FAILURES=0

echo "Building CogniPass from source for this CPU..."
if ! python scripts/install_cognipass.py --dest "$VIRTUAL_ENV/bin"; then
    echo "[ERROR] CogniPass was not installed. See the exact download/toolchain/build error above."
    INSTALL_FAILURES=$((INSTALL_FAILURES + 1))
fi

echo "Installing Advanced Web Scanner CLI tools..."
TOOLS_DIR="$VIRTUAL_ENV/bin"
mkdir -p "$TOOLS_DIR"
if ! python scripts/install_scanner_binaries.py --dest "$TOOLS_DIR"; then
    echo "[ERROR] One or more bundled scanner binaries were not installed. See the per-tool errors above."
    INSTALL_FAILURES=$((INSTALL_FAILURES + 1))
fi
echo "WPScan is not installed automatically because its official CLI requires Ruby and native build dependencies."

for scanner in naabu httpx nuclei; do
    if [ -x "$TOOLS_DIR/$scanner" ]; then
        echo "[OK] $scanner installed in $TOOLS_DIR"
    else
        echo "[WARNING] $scanner is not available; passive scanning will still work."
    fi
done
if command -v wpscan >/dev/null 2>&1; then
    echo "[OK] Existing WPScan installation detected"
else
    echo "[INFO] WPScan is optional and unavailable; Nuclei still covers signed WordPress exposure templates."
fi

echo "Downloading and building official Masscan 1.3.2 source for this OS/CPU..."
if ! python scripts/install_masscan.py --dest "$VIRTUAL_ENV/bin"; then
    echo "[ERROR] Masscan was not installed. See the exact download/compiler/build error above."
    INSTALL_FAILURES=$((INSTALL_FAILURES + 1))
fi

if [ "$INSTALL_FAILURES" -ne 0 ]; then
    echo ""
    echo "========================================"
    echo "Installation incomplete: $INSTALL_FAILURES required component group(s) failed."
    echo "Fix the errors above and rerun install.sh. Existing successful downloads/builds are safe to replace."
    echo "========================================"
    exit 1
fi

echo ""
echo "========================================"
echo "Installation complete!"
echo "Run 'python3 start.py' to launch Laitoxx."
echo "========================================"
