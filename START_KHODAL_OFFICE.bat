@echo off
chcp 65001 >nul
title Khodal Office Data Hub - Permanent Database Server

echo =====================================================================
echo           KHODAL OFFICE DATA HUB - PERMANENT DATABASE SERVER
echo =====================================================================
echo.
echo [1/3] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.10+ from python.org and add to PATH.
    pause
    exit /b 1
)

echo [2/3] Verifying SQLite Database (data\khodal_office.db)...
if not exist "data" mkdir "data"
if not exist "uploads" mkdir "uploads"
if not exist "exports" mkdir "exports"

echo [3/3] Starting Khodal Office Data Hub on http://localhost:8000 ...
echo.
echo ---------------------------------------------------------------------
echo   PERMANENT DATABASE ACTIVE: data\khodal_office.db
echo   Clearing browser history will NEVER delete your client records!
echo   All office data is permanently saved on your hard drive (D: drive).
echo.
echo   MASTER USERS:     manish  (Password: manish@7575)
echo                     admin   (Password: admin@7575)
echo   USER DATA STORE:  Permanently stored in database (khodal_office.db)
echo                     (No sensitive user/client data in browser storage)
echo ---------------------------------------------------------------------
echo.
echo Launching your browser now...
start "" "http://localhost:8000"

python app.py
pause
