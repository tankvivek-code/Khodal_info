@echo off
chcp 65001 >nul
title Khodal Office - Enable Automatic Windows Startup

echo =====================================================================
echo    KHODAL OFFICE DATA HUB - WINDOWS AUTO-STARTUP SETUP
echo =====================================================================
echo.
echo Setting up permanent background database server to run automatically
echo whenever your computer turns on...
echo.
cd /d "%~dp0"

powershell -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $su = [Environment]::GetFolderPath('Startup'); $s = $ws.CreateShortcut($su + '\KhodalOfficeServer.lnk'); $s.TargetPath = 'wscript.exe'; $s.Arguments = '"%~dp0START_KHODAL_OFFICE_SILENT.vbs"'; $s.WorkingDirectory = '%~dp0'; $s.Save()"

if errorlevel 0 (
    echo.
    echo =====================================================================
    echo   [SUCCESS] Automatic Windows Startup is now ENABLED!
    echo   Whenever your PC starts, the safe place database server will
    echo   automatically run in the background.
    echo   Your data is ALWAYS protected and safe on disk!
    echo =====================================================================
) else (
    echo [ERROR] Could not configure startup shortcut automatically.
)
echo.
pause
