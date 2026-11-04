@echo off
chcp 65001 >nul
title Stop Khodal Office Database Server

echo Stopping Khodal Office Database Server on port 8000...

for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo Stopping process PID %%a ...
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo Server stopped successfully.
ping -n 3 127.0.0.1 >nul
