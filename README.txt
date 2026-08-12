KP Local Testing Tool v1.4 - Python 3.12 Fix

PURPOSE
Local Windows website for KP calculation testing.

REQUIREMENTS
- Windows 10/11 64-bit
- Python 3.12 x64
- Windows Python Launcher (py)
- Internet connection during first setup

IMPORTANT FIX IN v1.4
- Replaced pyswisseph 2.10.3.2 with pysweph 2.10.3.6.
- pysweph provides a CPython 3.12 Windows x64 wheel.
- Python import remains: import swisseph as swe
- Added compatibility handling for the newer 13-entry house-cusp return layout.

RUN
1. Extract this ZIP to a NEW folder.
2. Double-click setup.bat.
3. Wait for SETUP SUCCESSFUL.
4. Double-click start.bat.
5. Website should open at http://127.0.0.1:8000
6. Keep the server window open while testing.

If setup fails, send a screenshot of the full error.
