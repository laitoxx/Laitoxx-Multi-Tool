@echo off
setlocal enabledelayedexpansion

echo ========================================
echo Laitoxx Windows Installer
echo ========================================

echo Checking Python version...
set VALID_PYTHON=

for %%P in (python python3) do (
    %%P -c "import sys; sys.exit(0 if (sys.version_info.major == 3 and 10 <= sys.version_info.minor <= 13) else 1)" 2>nul
    if !ERRORLEVEL! EQU 0 (
        set VALID_PYTHON=%%P
        goto :found_python
    )
)

:found_python
if "%VALID_PYTHON%"=="" (
    echo [ERROR] Valid Python ^<= 3.13 not found! 
    echo Python 3.14+ has known compatibility issues with PyQt6 and some dependencies during startup.
    echo Please go to https://www.python.org/downloads/ and download Python 3.12 or 3.13.
    pause
    exit /b 1
)

echo Found valid Python: %VALID_PYTHON%
echo Creating virtual environment in 'venv' folder...
%VALID_PYTHON% -m venv venv
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to create virtual environment. Ensure you have permissions.
    pause
    exit /b 1
)

echo Activating virtual environment and installing dependencies...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo Downloading vis-network for local rendering...
python acquire_vis_network.py

echo.
echo ========================================
echo Installation complete! 
echo Run 'python start.py' to launch Laitoxx.
echo ========================================
pause
