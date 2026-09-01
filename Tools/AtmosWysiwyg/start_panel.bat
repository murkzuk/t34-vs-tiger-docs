@echo off
cd /d "%~dp0"
start "atmos panel server" "C:\Users\Jeff\AppData\Local\Programs\Python\Python313\python.exe" atmos_server.py
timeout /t 2 /nobreak >nul
start "" http://127.0.0.1:8766
