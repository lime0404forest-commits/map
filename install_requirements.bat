@echo off
cd /d %~dp0
echo Installing from: %~dp0requirements.txt
py -3 -m pip install -r "%~dp0requirements.txt"
if errorlevel 1 pause
exit /b %errorlevel%
