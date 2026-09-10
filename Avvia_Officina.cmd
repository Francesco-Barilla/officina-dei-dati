@echo off
cd /d "%~dp0"
if exist "OfficinaDati.exe" (
    start "" "%~dp0OfficinaDati.exe"
    exit /b
)
python main.py
if errorlevel 1 (
    echo Installa Python e le dipendenze: python -m pip install -r requirements.txt
    pause
)
