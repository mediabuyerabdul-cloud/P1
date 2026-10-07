@echo off
cd /d "%~dp0"
where python >nul 2>nul || (echo Python install nahi hai: https://www.python.org/downloads/ ^(Add to PATH tick karein^) & pause & exit /b 1)
python -m pip install -q -r requirements.txt
python -m playwright install chromium
python src\decision_maker\app.py
pause
