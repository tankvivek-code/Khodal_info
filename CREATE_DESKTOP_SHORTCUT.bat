@echo off
chcp 65001 >nul
echo Creating Desktop Shortcut for Khodal Office Data Hub...

powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\Khodal Office Data Hub.lnk'); $s.TargetPath = '%~dp0START_KHODAL_OFFICE.bat'; $s.WorkingDirectory = '%~dp0'; $s.Description = 'Khodal Office Permanent Database Server'; $s.IconLocation = 'shell32.dll,23'; $s.Save()"

if errorlevel 0 (
    echo.
    echo =====================================================================
    echo   [SUCCESS] Shortcut 'Khodal Office Data Hub' created on your Desktop!
    echo   Double-click that icon anytime to start your permanent database!
    echo =====================================================================
) else (
    echo [ERROR] Could not create shortcut automatically.
)
pause
