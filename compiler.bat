@echo off
echo Compilando AutoCutter-AI...
echo.

REM Instalar PyInstaller se necessário
pip install pyinstaller --quiet

REM Compilar com PyInstaller
pyinstaller --onefile --windowed --name AutoCutter-AI src/gui/gui.py

echo.
echo Compilacao concluida!
echo Arquivo: dist/AutoCutter-AI.exe
pause