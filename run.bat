@echo off
title Khodal Office Data Hub
color 0B
echo =====================================================================
echo                 KHODAL OFFICE DATA HUB
echo          Daily Office Work Tracker, Search & Excel Storage
echo =====================================================================
echo.
cd /d "%~dp0"

:: Check Python
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    where py >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Python is not installed or not added to your system PATH!
        echo Please download and install Python from https://www.python.org/
        pause
        exit /b 1
    )
)

echo [1/2] Checking Python environment...
python -c "import fastapi, uvicorn, openpyxl, pandas" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Installing required packages...
    python -m pip install -r requirements.txt --quiet
)

echo.
echo [2/2] Starting Khodal Office Hub server...
echo ---------------------------------------------------------------------
echo Local URL:       http://localhost:8000
echo Office LAN:      Sharing active across office Wi-Fi
echo ---------------------------------------------------------------------
echo.
echo The browser will open automatically in 2 seconds...
echo Press Ctrl+C in this window anytime to stop the server.
echo =====================================================================
echo.

python app.py
pause
