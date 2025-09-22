@echo off
echo Compilando AutoCutter-AI com PyInstaller...
echo.

cd /d "%~dp0"

pyinstaller --noconfirm --onefile --windowed ^
--hidden-import PyQt5.QtWidgets ^
--hidden-import PyQt5.QtCore ^
--hidden-import PyQt5.QtGui ^
--hidden-import google.generativeai ^
--hidden-import yt_dlp ^
--hidden-import moviepy ^
--hidden-import sponsorblock ^
--add-data "src;src" ^
main.py

echo.
echo Compilacao concluida!
echo Executavel criado em: dist\main.exe
echo.
pause