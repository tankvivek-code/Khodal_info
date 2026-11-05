@echo off
chcp 65001 >nul
title Khodal Office - Allow Port 8000 in Windows Firewall

echo =====================================================================
echo    KHODAL OFFICE DATA HUB - WINDOWS FIREWALL CONFIGURATION
echo =====================================================================
echo.
echo This script allows other phones, tablets, and laptops on your office
echo Wi-Fi to connect to Khodal Office Hub on port 8000.
echo.

net session >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Running with Administrator privileges.
) else (
    echo [INFO] Requesting Administrator privileges...
    powershell -Command "Start-Process cmd -ArgumentList '/c netsh advfirewall firewall add rule name=\"Khodal Office Hub (Port 8000)\" dir=in action=allow protocol=TCP localport=8000 && pause' -Verb RunAs"
    exit /b
)

echo Adding Windows Firewall Inbound Rule for Port 8000...
netsh advfirewall firewall delete rule name="Khodal Office Hub (Port 8000)" >nul 2>&1
netsh advfirewall firewall add rule name="Khodal Office Hub (Port 8000)" dir=in action=allow protocol=TCP localport=8000

if %errorLevel% == 0 (
    echo.
    echo =====================================================================
    echo   [SUCCESS] Port 8000 is now OPEN in Windows Firewall!
    echo   Other devices on your Wi-Fi can now connect without being blocked.
    echo =====================================================================
) else (
    echo.
    echo [ERROR] Failed to add firewall rule. Please right-click this file
    echo and select 'Run as administrator'.
)

echo.
pause
