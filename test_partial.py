#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("Testando execução parcial do gui.py...")

# Parte 1: imports básicos
try:
    import sys
    import os
    import json
    import queue
    import threading
    import subprocess
    import tempfile
    import io

    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QLineEdit, QPushButton, QTextEdit, QProgressBar,
        QTabWidget, QGroupBox, QFormLayout, QSpinBox, QCheckBox,
        QFileDialog, QMessageBox, QComboBox, QListWidget, QSplitter,
        QFrame, QScrollArea, QRadioButton, QButtonGroup
    )
    from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
    from PyQt5.QtGui import QFont, QPalette, QColor

    print("✅ Imports básicos OK")
except Exception as e:
    print(f"❌ Erro nos imports básicos: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Parte 2: import do processing
try:
    from gui.processing import start_processing, start_bulk_download, detect_devices_thread
    print("✅ Import do processing OK")
except Exception as e:
    print(f"❌ Erro no import do processing: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Parte 3: configuração UTF-8
print("Tentando configuração UTF-8...")
try:
    print("Verificando sys.stdout.buffer...")
    if hasattr(sys.stdout, 'buffer') and sys.stdout.buffer is not None:
        print("Configurando sys.stdout...")
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    if hasattr(sys.stderr, 'buffer') and sys.stderr.buffer is not None:
        print("Configurando sys.stderr...")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

    print("Configurando variáveis de ambiente...")
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["PYTHONUTF8"] = "1"

    print("✅ Configuração UTF-8 OK")
except Exception as e:
    print(f"❌ Erro na configuração UTF-8: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("🎉 Todas as partes executadas com sucesso!")