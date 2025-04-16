@echo off
setlocal EnableDelayedExpansion
echo !PSModulePath! | findstr /L !USERPROFILE! >NUL
IF !ERRORLEVEL! EQU 0 goto :ISPOWERSHELL

set running_from_cmd=1

GOTO :start

:ISPOWERSHELL

:start

set VENV_PATH=.venv
set PYTHON=python

where !PYTHON! >nul 2>&1

if !errorlevel! neq 0 (
    set PYTHON=python3
    where !PYTHON! >nul 2>&1
    if !errorlevel! neq 0 (
        echo "ERROR: python nor python3 found in PATH!"
        exit /b 1
    )
)

if not exist "!VENV_PATH!" (
    echo "WARNING: Python venv dir not found..."
    echo "INFO: Creating Python venv in !VENV_PATH!..."
    !PYTHON! -m venv !VENV_PATH!
)

if !running_from_cmd! == 1 (
    call !VENV_PATH!\Scripts\activate.bat
) else (
    REM TODO: This doesn't work!!
    REM powershell -NoProfile -ExecutionPolicy Bypass -File !VENV_PATH!\Scripts\Activate.ps1
    echo "ERROR: Please run from inside a cmd, NOT a powershell (idk how to activate python venv from pwsh yet)
    exit /b 1
)

pip install --upgrade pip

pip install discord.py python-dotenv coloredlogs aiofile

python .\bot.py !*

deactivate
