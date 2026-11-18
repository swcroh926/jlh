@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
set "PYTHONUTF8=1"
rem This launcher asks for cost confirmation and a hidden OpenAI key.
set "DATA_DIR=%~dp0.local"
set "PYEXE="
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if not errorlevel 1 set "PYEXE=py -3"
if defined PYEXE goto ready
python -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if not errorlevel 1 set "PYEXE=python"
if defined PYEXE goto ready
echo Python 3.10 or newer is required.
echo Install from https://www.python.org/downloads/windows/
echo Select "Add python.exe to PATH" and run this file again.
pause
exit /b 1
:ready
echo Starting OpenAI preview. This window must remain open.
echo This mode can make BILLABLE API calls. The key prompt is hidden.
echo Browser address: http://127.0.0.1:8012
%PYEXE% -m backend.ai_preview
set "RESULT=%ERRORLEVEL%"
echo.
echo Preview stopped. If port 8012 is busy, close the previous preview window.
pause
exit /b %RESULT%
