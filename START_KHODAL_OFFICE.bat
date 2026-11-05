@echo off
chcp 65001 >nul
title Khodal Office Data Hub - Local Office Database Server

echo =====================================================================
echo         KHODAL OFFICE DATA HUB - LOCAL OFFICE SAFE PLACE
echo =====================================================================
echo.

cd /d "%~dp0"

echo [1/3] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please run SETUP_NEW_DEVICE.bat to configure this computer.
    pause
    exit /b 1
)

echo [2/3] Verifying SQLite Database Safe Place (data\khodal_office.db)...
if not exist "data" mkdir "data"
if not exist "data\backups" mkdir "data\backups"
if not exist "uploads" mkdir "uploads"
if not exist "exports" mkdir "exports"

set LAN_IP=
for /f "tokens=*" %%i in ('python -c "import socket; s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(('8.8.8.8', 80)); print(s.getsockname()[0]); s.close()" 2^>nul') do set LAN_IP=%%i

echo [3/3] Starting Local Database Server...
echo.
echo ---------------------------------------------------------------------
echo   [OK] LOCAL DATABASE ACTIVE: data\khodal_office.db
echo   Clearing browser history will NEVER delete your client records!
echo   All office data is permanently saved on this computer's hard drive.
echo.
echo   💻 THIS COMPUTER:   http://localhost:8000
if not "%LAN_IP%"=="" (
echo   📱 OTHER DEVICES:   http://%LAN_IP%:8000
echo                       (Connect phones/laptops to the same Wi-Fi)
)
echo.
echo   MASTER USERS:      manish  (Password: manish@7575)
echo                      admin   (Password: admin@7575)
echo.
echo   NOTE: If other devices cannot connect, double-click:
echo         ALLOW_FIREWALL_PORT_8000.bat
echo ---------------------------------------------------------------------
echo.
echo Launching your browser now at http://localhost:8000 ...
start http://localhost:8000
python app.py
pause
