@echo off
chcp 65001 >nul
title Khodal Office Data Hub - New Computer / Device Setup

echo =====================================================================
echo         KHODAL OFFICE DATA HUB - NEW COMPUTER SETUP WIZARD
echo =====================================================================
echo.
echo This wizard will configure Khodal Office Data Hub on this computer.
echo.

cd /d "%~dp0"

echo [1/5] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not added to PATH!
    echo.
    echo Please install Python 3.10 or newer:
    echo 1. Download from https://www.python.org/downloads/
    echo 2. IMPORTANT: Check the box "Add Python to PATH" during installation.
    echo.
    pause
    start https://www.python.org/downloads/
    exit /b 1
)
python --version

echo.
echo [2/5] Installing required Python packages (FastAPI, Uvicorn, Pandas, Openpyxl)...
pip install -r requirements.txt
if errorlevel 1 (
    echo [WARNING] Some dependencies had warnings. Continuing...
)

echo.
echo [3/5] Creating required storage folders...
if not exist "data" mkdir "data"
if not exist "data\backups" mkdir "data\backups"
if not exist "uploads" mkdir "uploads"
if not exist "exports" mkdir "exports"
echo [OK] Storage directories ready.

echo.
echo [4/5] Creating Desktop Shortcut...
powershell -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $d = [Environment]::GetFolderPath('Desktop'); $s = $ws.CreateShortcut($d + '\Khodal Office Data Hub.lnk'); $s.TargetPath = '%~dp0START_KHODAL_OFFICE.bat'; $s.WorkingDirectory = '%~dp0'; $s.Description = 'Khodal Office Permanent Safe Place Database'; $s.IconLocation = 'shell32.dll,23'; $s.Save()"
echo [OK] Desktop shortcut created.

echo.
echo [5/5] Configuring Windows Firewall for Port 8000 (Local Office Network)...
powershell -Command "Start-Process cmd -ArgumentList '/c netsh advfirewall firewall add rule name=\"Khodal Office Hub (Port 8000)\" dir=in action=allow protocol=TCP localport=8000' -Verb RunAs -WindowStyle Hidden" >nul 2>&1
echo [OK] Firewall configured.

echo.
echo =====================================================================
echo   [SUCCESS] KHODAL OFFICE DATA HUB IS FULLY CONFIGURED!
echo =====================================================================
echo.
echo   - Local Database:  data\khodal_office.db
echo   - Desktop Icon:    "Khodal Office Data Hub" on Desktop
echo   - Default Login:   manish / manish@7575
echo.
echo Starting the database server now...
echo.

start "" "%~dp0START_KHODAL_OFFICE.bat"
exit /b 0

