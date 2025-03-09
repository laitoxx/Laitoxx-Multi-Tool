@echo off
chcp 65001 >nul
title Laitoxx Manager
color 0C

:CHOOSE_LANGUAGE
cls
echo Choose your language / Выберите язык:
echo 1. English
echo 2. Русский
set /p langChoice=Enter your choice / Введите ваш выбор: 
if "%langChoice%"=="1" goto ENGLISH
if "%langChoice%"=="2" goto RUSSIAN
echo Invalid choice, please try again.
goto CHOOSE_LANGUAGE

:ENGLISH
cls
echo Welcome.
echo Do you want to install Python dependencies? (y/n)
set /p installChoice=:
if /i "%installChoice%"=="y" goto INSTALL_DEPENDENCIES_EN
if /i "%installChoice%"=="n" goto SELECT_PROGRAM_EN
echo Invalid choice, please try again.
goto ENGLISH

:RUSSIAN
cls
echo Добро пожаловать.
echo Хотите установить зависимости Python? (д/н)
set /p installChoice=:
if /i "%installChoice%"=="д" goto INSTALL_DEPENDENCIES_RU
if /i "%installChoice%"=="н" goto SELECT_PROGRAM_RU
echo Неверный выбор, попробуйте снова.
goto RUSSIAN

:INSTALL_DEPENDENCIES_EN
cls
echo Installing Python dependencies...
pip install -r requirements.txt
if %errorlevel%==0 (
    echo Dependencies installed successfully.
    pause
    goto SELECT_PROGRAM_EN
) else (
    echo Error installing dependencies. Please check your requirements.txt or Python setup.
    pause
    goto SELECT_PROGRAM_EN
)

:INSTALL_DEPENDENCIES_RU
cls
echo Устанавливаем зависимости Python...
pip install -r requirements.txt
if %errorlevel%==0 (
    echo Зависимости успешно установлены.
    pause
    goto SELECT_PROGRAM_RU
) else (
    echo Ошибка установки зависимостей. Проверьте файл requirements.txt или установку Python.
    pause
    goto SELECT_PROGRAM_RU
)

:SELECT_PROGRAM_EN
cls
echo Choose what to run:
echo 1. Laitoxx.py
echo 2. Laitoxx.exe
set /p launchChoice=:
if "%launchChoice%"=="1" python laitoxx.py
if "%launchChoice%"=="2" start laitoxx.exe
if not "%launchChoice%"=="1" if not "%launchChoice%"=="2" (
    echo Invalid choice, please try again.
    goto SELECT_PROGRAM_EN
)
goto END

:SELECT_PROGRAM_RU
cls
echo Выберите, что запустить:
echo 1. Laitoxx.py
echo 2. Laitoxx.exe
set /p launchChoice=:
if "%launchChoice%"=="1" python laitoxx.py
if "%launchChoice%"=="2" start laitoxx.exe
if not "%launchChoice%"=="1" if not "%launchChoice%"=="2" (
    echo Неверный выбор, попробуйте снова.
    goto SELECT_PROGRAM_RU
)
goto END

:END
pause
exit
