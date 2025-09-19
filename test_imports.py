#!/usr/bin/env python3
import sys
import os
import traceback
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("Testando importações...")

try:
    from PyQt5.QtWidgets import QApplication
    print("✅ PyQt5 importado com sucesso")
except Exception as e:
    print(f"❌ Erro ao importar PyQt5: {e}")
    sys.exit(1)

# Tentar executar o gui.py linha por linha
print("Executando gui.py...")

try:
    exec(open(os.path.join(os.path.dirname(__file__), 'src', 'gui', 'gui.py'), encoding='utf-8').read())
    print("✅ gui.py executado com sucesso")
except Exception as e:
    print(f"❌ Erro ao executar gui.py: {e}")
    traceback.print_exc()
    sys.exit(1)

print("🎉 Teste concluído!")