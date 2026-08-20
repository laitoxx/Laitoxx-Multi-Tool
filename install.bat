@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

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
if %ERRORLEVEL% NEQ 0 echo [WARNING] pip could not be upgraded; continuing with the bundled version.
python -m pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python dependencies could not be installed from requirements.txt.
    echo Check the pip error above ^(network/TLS, unsupported Python wheel, compiler, or system headers^), then retry.
    pause
    exit /b 1
)

set INSTALL_FAILURES=0

echo.
echo Building CogniPass from source for this CPU...
python scripts\install_cognipass.py --dest "%VIRTUAL_ENV%\Scripts"
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] CogniPass was not installed. See the exact download/toolchain/build error above.
    set /a INSTALL_FAILURES+=1
)

echo.
echo Installing Advanced Web Scanner CLI tools...
call :install_scanner_tools
if %ERRORLEVEL% NEQ 0 set /a INSTALL_FAILURES+=1

echo.
echo Downloading and building official Masscan 1.3.2 source for Windows...
echo Security software may flag raw-packet scanners. Keep protection enabled and allow only the verified source build if authorized.
python scripts\install_masscan.py --dest "%VIRTUAL_ENV%\Scripts"
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Masscan was not installed. See the exact download/compiler/build error above.
    set /a INSTALL_FAILURES+=1
)

if !INSTALL_FAILURES! NEQ 0 (
    echo.
    echo ========================================
    echo Installation incomplete: !INSTALL_FAILURES! required component group^(s^) failed.
    echo Fix the errors above and rerun install.bat.
    echo ========================================
    pause
    exit /b 1
)

echo.
echo ========================================
echo Installation complete! 
echo Run 'python start.py' to launch Laitoxx.
echo ========================================
pause
exit /b 0

:install_scanner_tools
set "TOOLS_DIR=%VIRTUAL_ENV%\Scripts"
python scripts\install_scanner_binaries.py --dest "!TOOLS_DIR!"
set SCANNER_RESULT=!ERRORLEVEL!
if !SCANNER_RESULT! NEQ 0 echo [ERROR] One or more bundled scanner binaries were not installed. See the per-tool errors above.
echo WPScan is not installed automatically because its official CLI requires Ruby and native build dependencies.

for %%S in (naabu.exe httpx.exe nuclei.exe) do (
    if exist "!TOOLS_DIR!\%%S" (
        echo [OK] %%S installed in !TOOLS_DIR!
    ) else (
        echo [WARNING] %%S is not available; passive scanning will still work.
    )
)
where wpscan >nul 2>nul
if !ERRORLEVEL! EQU 0 (
    echo [OK] Existing WPScan installation detected.
) else (
    echo [INFO] WPScan is optional and unavailable; Nuclei still covers signed WordPress exposure templates.
)
exit /b !SCANNER_RESULT!
