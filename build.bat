@echo off
rem Crea dist\Ricevute.exe su Windows
cd /d "%~dp0"
py -3 -m venv .venv
.venv\Scripts\pip install -q -r requirements.txt pyinstaller
.venv\Scripts\pyinstaller --noconfirm --clean --windowed --onefile --name Ricevute ^
  --add-data "font:font" --exclude-module pydoc --exclude-module numpy ricevute.py
echo Fatto: guarda nella cartella dist\
pause
