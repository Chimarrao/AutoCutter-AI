# AutoCutter-AI - Executável

## Como usar o executável

O executável `main.exe` foi compilado com PyInstaller e inclui todas as dependências necessárias.

### Localização
- **Executável**: `dist/main.exe`
- **Tamanho**: ~243MB

### Funcionalidades incluídas
- ✅ Interface PyQt5 completa
- ✅ Processamento de vídeos
- ✅ Download do YouTube
- ✅ Geração de clipes com IA
- ✅ Video Maker com edição avançada

### Como executar
1. Navegue até a pasta `dist/`
2. Execute o arquivo `main.exe`
3. A interface gráfica será aberta

### Requisitos do sistema
- Windows 10/11
- Não requer Python instalado
- Todas as dependências estão incluídas no executável

### Compilação
Para recompilar o executável, execute:
```batch
build.bat
```

Ou use o comando PyInstaller diretamente:
```batch
pyinstaller --noconfirm --onefile --windowed --hidden-import PyQt5.QtWidgets --hidden-import PyQt5.QtCore --hidden-import PyQt5.QtGui --hidden-import google.generativeai --hidden-import yt_dlp --hidden-import moviepy --hidden-import sponsorblock --add-data "src;src" main.py
```

### Notas importantes
- O executável inclui FFmpeg e todas as bibliotecas necessárias
- Arquivos temporários são criados na pasta `temp/`
- Vídeos processados são salvos na pasta `prontos/`
- Downloads do YouTube vão para `downloads/` e `bulk_download/`