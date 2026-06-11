@echo off
cd /d "%~dp0"

:: Kill any existing python bot instances
powershell -Command "Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*bot.py*' } | Stop-Process -Force"
timeout /t 2 /nobreak >NUL

:: Run bot using venv python directly
echo Starting bot...
start "" /B venv\Scripts\python.exe bot.py
