@echo off
REM Build a single-file exe: dist\HEIC2JPG.exe
REM Requires Python 3.10+
python -m pip install -r requirements.txt pyinstaller || exit /b 1
python -m PyInstaller --noconfirm --onefile --windowed --name HEIC2JPG ^
  --collect-all tkinterdnd2 --collect-all pi_heif heic2jpg.py
