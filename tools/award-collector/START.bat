@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYEXE="
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if not errorlevel 1 set "PYEXE=py -3"
if defined PYEXE goto ready
python -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if not errorlevel 1 set "PYEXE=python"
if defined PYEXE goto ready
echo Python 3.10 or newer is required.
echo Install Python from https://www.python.org/downloads/windows/
echo Enable "Add python.exe to PATH", then run START.bat again.
pause
exit /b 1
:ready
echo Collecting award titles. Please wait.
echo Existing completed pages will be skipped.
%PYEXE% collector.py %*
set "RESULT=%ERRORLEVEL%"
echo.
if "%RESULT%"=="0" (echo Finished.) else (echo Some steps failed. Please check output\collector.log.)
if exist "output" start "" explorer.exe "%CD%\output"
pause
exit /b %RESULT%
