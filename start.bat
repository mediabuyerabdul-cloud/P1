@echo off
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python install nahi hai. https://www.python.org/downloads/ se install karein
  echo Install karte waqt "Add python.exe to PATH" zaroor tick karein.
  pause
  exit /b 1
)
python -m pip install -q -r requirements.txt
python src\downloader\app.py
pause
