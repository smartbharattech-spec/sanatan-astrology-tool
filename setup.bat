@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ==========================================
echo KP Local Testing Tool - Windows Setup v1.4
echo ==========================================
echo.

echo Looking specifically for Python 3.12 64-bit...
py -3.12 -c "import sys,struct; print('Python:',sys.version.split()[0]); print('Architecture:',struct.calcsize('P')*8,'bit'); raise SystemExit(0 if sys.version_info[:2]==(3,12) and struct.calcsize('P')*8==64 else 2)"
if errorlevel 2 goto BAD_PYTHON
if errorlevel 1 goto NO_PYTHON312

echo.
echo Python 3.12 found.

if exist ".venv\Scripts\python.exe" goto CHECK_EXISTING_VENV

:CREATE_VENV
echo.
echo Creating Python 3.12 virtual environment...
if exist ".venv" rmdir /s /q ".venv"
py -3.12 -m venv ".venv"
if errorlevel 1 goto FAIL
goto VENV_READY

:CHECK_EXISTING_VENV
".venv\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info[:2]==(3,12) else 1)" >nul 2>nul
if errorlevel 1 goto CREATE_VENV

:VENV_READY
set "VPY=%CD%\.venv\Scripts\python.exe"
if not exist "%VPY%" goto FAIL

echo.
echo Upgrading pip, setuptools and wheel...
"%VPY%" -m pip install --upgrade pip setuptools wheel
if errorlevel 1 goto FAIL

echo.
echo Installing Swiss Ephemeris...
"%VPY%" -m pip install --only-binary=:all: pysweph==2.10.3.6
if errorlevel 1 goto SWISS_FAIL

echo.
echo Installing web application dependencies...
"%VPY%" -m pip install "fastapi>=0.115,<1.0" "uvicorn[standard]>=0.30,<1.0"
if errorlevel 1 goto FAIL

echo.
echo Verifying complete installation...
"%VPY%" -c "import sys,swisseph,fastapi,uvicorn; print('Runtime Python:',sys.version.split()[0]); print('Swiss Ephemeris:',swisseph.version); print('FastAPI:',fastapi.__version__); print('Uvicorn:',uvicorn.__version__)"
if errorlevel 1 goto FAIL

echo.
echo ==========================================
echo SETUP SUCCESSFUL
echo ==========================================
echo KP Tool is isolated on Python 3.12.
echo Your Python 3.14 installation is unchanged.
echo Now run start.bat.
echo.
pause
exit /b 0

:NO_PYTHON312
echo.
echo ERROR: Python 3.12 64-bit was not found by the Windows Python Launcher.
echo Install Python 3.12 x64 side-by-side with Python 3.14.
echo During install, enable the Python Launcher option.
echo Then run setup.bat again.
goto FAIL_END

:BAD_PYTHON
echo.
echo ERROR: Python 3.12 was found but is not a compatible 64-bit installation.
goto FAIL_END

:SWISS_FAIL
echo.
echo ERROR: pysweph 2.10.3.6 for Python 3.12 x64 could not be installed.
goto FAIL_END

:FAIL
echo.
echo ERROR: A setup command failed.

:FAIL_END
echo.
echo ==========================================
echo SETUP FAILED
echo ==========================================
echo Do not run start.bat yet.
echo Send a screenshot of the error above.
echo.
pause
exit /b 1
