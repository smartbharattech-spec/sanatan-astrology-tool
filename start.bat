@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "VPY=%CD%\.venv\Scripts\python.exe"
if not exist "%VPY%" goto NOT_READY

"%VPY%" -c "import sys,swisseph,fastapi,uvicorn; raise SystemExit(0 if sys.version_info[:2]==(3,12) else 1)" >nul 2>nul
if errorlevel 1 goto NOT_READY

echo ==========================================
echo KP Local Testing Tool
echo Python 3.12 isolated runtime
echo ==========================================
echo.
echo On this PC:        http://127.0.0.1:8000
echo On your phone (same WiFi): http://YOUR-PC-LAN-IP:8000
echo   Find your PC's LAN IP: open cmd, run "ipconfig", look for
echo   "IPv4 Address" under your active WiFi/Ethernet adapter (e.g. 192.168.1.5)
echo Keep this window open while using the website.
echo Press Ctrl+C to stop the server.
echo.

start "" "http://127.0.0.1:8000"
"%VPY%" -m uvicorn app.main:app --host 0.0.0.0 --port 8000

echo.
echo Local server stopped.
pause
exit /b 0

:NOT_READY
echo ERROR: Python 3.12 environment is not ready.
echo Run setup.bat first and confirm SETUP SUCCESSFUL.
pause
exit /b 1
