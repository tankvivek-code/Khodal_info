@echo off
chcp 65001 >nul
title Create Desktop Shortcut - Khodal Office

echo Creating Desktop Shortcut for Khodal Office Data Hub...
cd /d "%~dp0"

powershell -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $d = [Environment]::GetFolderPath('Desktop'); $s = $ws.CreateShortcut($d + '\Khodal Office Data Hub.lnk'); $s.TargetPath = '%~dp0START_KHODAL_OFFICE.bat'; $s.WorkingDirectory = '%~dp0'; $s.Description = 'Khodal Office Permanent Safe Place Database'; $s.IconLocation = 'shell32.dll,23'; $s.Save()"

if errorlevel 0 (
    echo.
    echo =====================================================================
    echo   [SUCCESS] Shortcut 'Khodal Office Data Hub' created on your Desktop!
    echo   Double-click that desktop icon anytime to start your database!
    echo =====================================================================
) else (
    echo [ERROR] Could not create shortcut automatically.
)
echo.
pause
