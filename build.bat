@echo off
REM 打包为单文件 exe, 输出在 dist\HEIC2JPG.exe
REM 需要 Python 3.10+
python -m pip install -r requirements.txt pyinstaller || exit /b 1
python -m PyInstaller --noconfirm --onefile --windowed --name HEIC2JPG ^
  --collect-all tkinterdnd2 --collect-all pi_heif heic2jpg.py
