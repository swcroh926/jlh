@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
set "PYTHONUTF8=1"
rem This launcher is a no-cost preview. Do not inherit any API keys.
set "LLM_API_KEY="
set "OPENAI_API_KEY="
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
echo Starting local preview. This window must remain open.
echo AI API calls are disabled in this launcher.
echo Browser address: http://127.0.0.1:8012
%PYEXE% -m backend.server --port 8012 --open-browser
set "RESULT=%ERRORLEVEL%"
echo.
echo Preview stopped. If port 8012 is busy, close the previous preview window.
pause
exit /b %RESULT%
