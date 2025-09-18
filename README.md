# AutoCutter-AI

Gerador automático de clipes de vídeo usando Inteligência Artificial para identificar momentos interessantes em vídeos do YouTube.

## Instalação

### Pré-requisitos
- Python >= 3.10
- FFmpeg (para processamento de vídeo)
- GPU NVIDIA (opcional, para aceleração CUDA) ou AMD (opcional, para VAAPI/rocm)

### Instalando Python
Baixe e instale Python 3.10 ou superior do site oficial: https://www.python.org/downloads/

### Instalando FFmpeg
#### Windows
1. Baixe o FFmpeg do site oficial: https://ffmpeg.org/download.html
2. Extraia o arquivo zip
3. Adicione o caminho da pasta `bin` ao PATH do sistema

#### Linux
```bash
sudo apt update
sudo apt install ffmpeg
```

### Instalando dependências Python
```bash
pip install -r requirements.txt
```

## Estrutura do Projeto

```
/src
  /gui        -> Interface PyQt5
  /download   -> Lógica yt-dlp para downloads
  /processing -> Processamento FFmpeg
  /utils      -> Funções auxiliares (detecção GPU/CPU, paths, etc.)
main.py       -> Ponto de entrada
requirements.txt
README.md
```

## Uso

### Execução
```bash
python main.py
```

### Funcionalidades
- **Geração de Clipes**: Identifica automaticamente momentos interessantes em vídeos usando IA
- **Download YouTube**: Baixe vídeos simples ou em massa do YouTube
- **Processamento Avançado**: Configurações para duração máxima de segmentos, pastas temporárias
- **Vídeo Maker**: Funções para converter vídeos (centro, esquerda, direita) com sponsor block, barras pretas, etc.

### Suporte GPU/CPU
O sistema detecta automaticamente GPUs disponíveis (NVIDIA, AMD) e permite escolher entre CPU ou GPU para processamento FFmpeg.
- NVIDIA: usa `-hwaccel cuda`
- AMD: usa `-hwaccel vaapi` ou `rocm`
- CPU: processamento padrão

### Lista de CPUs e GPUs
A interface mostra todas as CPUs e GPUs detectadas no sistema, permitindo seleção manual.

## Desenvolvimento
Para contribuir ou modificar o código, siga a estrutura de pastas recomendada e use PyQt5 para a interface gráfica.