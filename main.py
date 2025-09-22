#!/usr/bin/env python3
"""
AutoCutter-AI - Gerador automático de clipes de vídeo usando IA
Launcher principal da aplicação
"""

import sys
import os

# Adicionar src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

if __name__ == "__main__":
    # Importar e executar a função main do GUI
    from gui.gui import main
    main()