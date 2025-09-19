#!/usr/bin/env python3
"""
Módulo de processamento para AutoCutter-AI
Contém funções de processamento de vídeo e download
"""

import os
import sys
import threading
import subprocess
import queue
import yt_dlp
import urllib.parse
import unicodedata
import re
import io

# força UTF-8 como padrão
if hasattr(sys.stdout, 'buffer') and sys.stdout.buffer is not None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
if hasattr(sys.stderr, 'buffer') and sys.stderr.buffer is not None:
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUTF8"] = "1"

def normalize_filename(filename):
    """Remove acentos e substitui espaços por underscores no nome do arquivo"""
    # Remove acentos
    normalized = unicodedata.normalize('NFD', filename)
    ascii_filename = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')

    # Substitui espaços por underscores
    ascii_filename = ascii_filename.replace(' ', '_')

    # Remove caracteres especiais exceto pontos, hífens e underscores
    ascii_filename = re.sub(r'[^\w\-_\.]', '', ascii_filename)

    return ascii_filename

def is_valid_youtube_url(url):
    """Validar se a URL é válida do YouTube"""
    try:
        parsed_url = urllib.parse.urlparse(url)
        if parsed_url.netloc in ['www.youtube.com', 'youtube.com', 'youtu.be', 'm.youtube.com']:
            return True
        return False
    except:
        return False

def start_processing(gui_instance):
    """Implementar processamento de vídeo"""
    # Validação básica
    if not gui_instance.video_path:
        QMessageBox.warning(gui_instance, "Erro", "Por favor, selecione um arquivo de vídeo!")
        return

    if not os.path.exists(gui_instance.video_path):
        QMessageBox.warning(gui_instance, "Erro", "O arquivo de vídeo não existe!")
        return

    if not gui_instance.output_dir:
        QMessageBox.warning(gui_instance, "Erro", "Por favor, especifique uma pasta de saída!")
        return

    if gui_instance.is_processing:
        QMessageBox.warning(gui_instance, "Aviso", "Já existe um processamento em andamento!")
        return

    # Salvar configurações se API key fornecida
    if gui_instance.api_key:
        gui_instance.save_config()

    # Iniciar processamento
    gui_instance.is_processing = True
    gui_instance.process_btn.setEnabled(False)
    gui_instance.tab_widget.setCurrentIndex(3)  # Aba de processamento
    gui_instance.progress_bar.setValue(0)
    gui_instance.log_text.clear()

    # Iniciar thread de processamento
    thread = threading.Thread(target=process_video_thread, args=(gui_instance,), daemon=True)
    thread.start()

def process_video_thread(gui_instance):
    """Thread para processamento de vídeo"""
    try:
        # Criar pastas necessárias
        os.makedirs(gui_instance.output_dir, exist_ok=True)
        os.makedirs(gui_instance.temp_dir, exist_ok=True)

        # Comando básico para processamento
        cmd = [
            sys.executable, "generateClips.py",
            gui_instance.video_path,
            "--output-dir", gui_instance.output_dir,
            "--min-clips", str(gui_instance.min_clips),
            "--max-clips", str(gui_instance.max_clips),
            "--whisper-model", gui_instance.whisper_model
        ]

        if gui_instance.api_key:
            cmd.extend(["--api-key", gui_instance.api_key])

        if not gui_instance.captions:
            cmd.append("--no-captions")

        gui_instance.output_queue.put(("log", f"Comando: {' '.join(cmd)}\n"))
        gui_instance.output_queue.put(("status", "🎬 Iniciando processamento..."))

        # Executar comando
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        # Ler saída em tempo real
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                gui_instance.output_queue.put(("log", output))

                # Atualizar progresso baseado na saída
                if "Process complete" in output or "completed successfully" in output:
                    gui_instance.output_queue.put(("progress", 100))
                    gui_instance.output_queue.put(("status", "🎉 Processamento concluído!"))
                elif "Error" in output.lower():
                    gui_instance.output_queue.put(("status", "❌ Erro detectado"))

        # Verificar resultado
        return_code = process.poll()
        if return_code == 0:
            gui_instance.output_queue.put(("finished", True))
        else:
            gui_instance.output_queue.put(("finished", False))

    except Exception as e:
        gui_instance.output_queue.put(("error", str(e)))
        gui_instance.output_queue.put(("finished", False))

def start_bulk_download(gui_instance):
    """Iniciar download em massa de vídeos"""
    urls_text = gui_instance.bulk_urls_text.toPlainText().strip()

    if not urls_text:
        QMessageBox.warning(gui_instance, "Erro", "Por favor, adicione URLs para download!")
        return

    urls = [url.strip() for url in urls_text.split("\n") if url.strip()]

    if not urls:
        QMessageBox.warning(gui_instance, "Erro", "Nenhuma URL válida encontrada!")
        return

    if gui_instance.is_downloading:
        QMessageBox.warning(gui_instance, "Aviso", "Já existe um download em andamento!")
        return

    # Criar pasta de download em massa se não existir
    os.makedirs(gui_instance.bulk_download_dir, exist_ok=True)

    # Iniciar download em thread separada
    gui_instance.is_downloading = True
    gui_instance.bulk_download_btn.setEnabled(False)
    gui_instance.tab_widget.setCurrentIndex(3)  # Mudar para aba de processamento
    gui_instance.progress_bar.setValue(0)
    gui_instance.log_text.clear()

    thread = threading.Thread(target=bulk_download_thread, args=(gui_instance, urls), daemon=True)
    thread.start()

def bulk_download_thread(gui_instance, urls):
    """Thread para download em massa de vídeos"""
    try:
        total_urls = len(urls)
        downloaded = 0
        failed = 0

        gui_instance.output_queue.put(("log", f"📥 Iniciando download de {total_urls} vídeos...\n"))
        gui_instance.output_queue.put(("log", f"📁 Pasta de destino: {gui_instance.bulk_download_dir}\n\n"))

        for i, url in enumerate(urls, 1):
            if not is_valid_youtube_url(url):
                gui_instance.output_queue.put(("log", f"❌ URL inválida: {url}\n"))
                failed += 1
                continue

            gui_instance.output_queue.put(("status", f"📥 Baixando {i}/{total_urls}: {url[:50]}..."))
            gui_instance.output_queue.put(("log", f"🔄 Processando {i}/{total_urls}: {url}\n"))

            try:
                def progress_hook(d):
                    if d['status'] == 'downloading':
                        try:
                            # Calcular progresso global
                            video_progress = 0
                            if 'total_bytes' in d and d['total_bytes']:
                                video_progress = (d['downloaded_bytes'] / d['total_bytes']) * 100
                            elif 'total_bytes_estimate' in d and d['total_bytes_estimate']:
                                video_progress = (d['downloaded_bytes'] / d['total_bytes_estimate']) * 100

                            # Progresso global considerando todos os vídeos
                            global_progress = ((i - 1) / total_urls) * 100 + (video_progress / total_urls)
                            gui_instance.output_queue.put(("progress", min(global_progress, 95)))

                            # Atualizar status com informações de download
                            speed = d.get('speed', 0)
                            if speed:
                                speed_mb = speed / 1024 / 1024
                                gui_instance.output_queue.put(("status", f"📥 Baixando {i}/{total_urls} - {speed_mb:.1f} MB/s"))

                        except Exception as e:
                            gui_instance.output_queue.put(("log", f"Erro ao processar progresso: {e}\n"))

                    elif d['status'] == 'finished':
                        filename = os.path.basename(d['filename'])
                        # Normalizar o nome do arquivo
                        normalized_filename = filename
                        if normalized_filename != filename:
                            old_path = d['filename']
                            new_path = os.path.join(os.path.dirname(old_path), normalized_filename)
                            try:
                                os.rename(old_path, new_path)
                                gui_instance.output_queue.put(("log", f"📝 Arquivo renomeado: {filename} → {normalized_filename}\n"))
                            except Exception as e:
                                gui_instance.output_queue.put(("log", f"⚠️ Erro ao renomear arquivo: {e}\n"))

                        gui_instance.output_queue.put(("log", f"✅ Download concluído: {normalized_filename}\n"))

                # Configurações do yt-dlp
                ydl_opts = {
                    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4',
                    'outtmpl': os.path.join(gui_instance.bulk_download_dir, '%(title)s.%(ext)s'),
                    'progress_hooks': [progress_hook],
                    'noplaylist': True,
                    'writesubtitles': False,
                    'writeautomaticsub': False,
                    'writethumbnail': True,  # Sempre baixar thumbnails
                }

                # Configurar formato das thumbnails
                ydl_opts['postprocessors'] = ydl_opts.get('postprocessors', [])
                ydl_opts['postprocessors'].append({
                    'key': 'FFmpegThumbnailsConvertor',
                    'format': 'jpg',
                })

                # Verificar se é apenas áudio (baseado na qualidade selecionada)
                quality = gui_instance.quality_combo.currentText()
                if quality == "audio":
                    if 'postprocessors' not in ydl_opts:
                        ydl_opts['postprocessors'] = []
                    ydl_opts['postprocessors'].append({
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    })
                    ydl_opts['merge_output_format'] = 'mp3'
                else:
                    ydl_opts['merge_output_format'] = 'mp4'

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    # Obter informações do vídeo primeiro
                    info = ydl.extract_info(url, download=False)
                    title = info.get('title', 'Vídeo sem título')
                    uploader = info.get('uploader', 'Desconhecido')
                    duration = info.get('duration', 0)

                    gui_instance.output_queue.put(("log", f"📽️ Título: {title}\n"))
                    gui_instance.output_queue.put(("log", f"📝 Canal: {uploader}\n"))
                    gui_instance.output_queue.put(("log", f"⏱️ Duração: {duration // 60}:{duration % 60:02d}\n"))

                    # Verificar se já existe
                    normalized_title = title
                    ext = 'mp3' if quality == "audio" else 'mp4'
                    expected_filename = os.path.join(gui_instance.bulk_download_dir, f"{normalized_title}.{ext}")

                    if os.path.exists(expected_filename):
                        gui_instance.output_queue.put(("log", f"📁 Arquivo já existe, pulando: {normalized_title}.{ext}\n"))
                        downloaded += 1
                    else:
                        # Baixar o vídeo
                        ydl.download([url])
                        downloaded += 1

                    gui_instance.output_queue.put(("log", f"✅ Processado {i}/{total_urls}\n\n"))

            except Exception as e:
                gui_instance.output_queue.put(("log", f"❌ Erro ao baixar {url}: {str(e)}\n\n"))
                failed += 1

            # Atualizar progresso global
            global_progress = (i / total_urls) * 100
            gui_instance.output_queue.put(("progress", global_progress))

        # Finalizar
        gui_instance.output_queue.put(("progress", 100))
        gui_instance.output_queue.put(("status", f"✅ Download em massa concluído!"))
        gui_instance.output_queue.put(("log", f"\n🎉 Download em massa finalizado!\n"))
        gui_instance.output_queue.put(("log", f"✅ Sucessos: {downloaded}\n"))
        gui_instance.output_queue.put(("log", f"❌ Falhas: {failed}\n"))
        gui_instance.output_queue.put(("log", f"📁 Pasta: {gui_instance.bulk_download_dir}\n"))

        gui_instance.output_queue.put(("bulk_download_finished", True))

    except Exception as e:
        error_msg = str(e)
        gui_instance.output_queue.put(("log", f"❌ Erro no download em massa: {error_msg}\n"))
        gui_instance.output_queue.put(("status", "❌ Erro no download em massa"))
        gui_instance.output_queue.put(("bulk_download_finished", False))

def detect_devices_thread(gui_instance):
    """Thread para detectar dispositivos com barra de progresso - versão leve sem torch"""
    try:
        devices = []

        # Etapa 1: Detectar CPUs
        gui_instance.output_queue.put(("device_progress", 25))
        gui_instance.output_queue.put(("device_status", "Detectando CPU..."))
        try:
            import platform
            cpu_info = platform.processor()
            if cpu_info and cpu_info.strip():
                devices.append(f"CPU: {cpu_info}")
            else:
                devices.append("CPU: Disponível")
        except Exception as e:
            devices.append(f"CPU: Disponível (erro: {str(e)})")

        # Etapa 2: Detectar GPUs NVIDIA (método leve)
        gui_instance.output_queue.put(("device_progress", 50))
        gui_instance.output_queue.put(("device_status", "Detectando GPUs NVIDIA..."))
        try:
            # Usar nvidia-mlpy3 ou método alternativo mais leve
            result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader,nounits'],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                gpu_lines = result.stdout.strip().split('\n')
                for i, line in enumerate(gpu_lines):
                    if line.strip() and ',' in line:
                        name, memory = line.split(',', 1)
                        devices.append(f"NVIDIA GPU {i}: {name.strip()} ({memory.strip()})")
            else:
                devices.append("NVIDIA: Não detectado")
        except subprocess.TimeoutExpired:
            devices.append("NVIDIA: Timeout na detecção")
        except FileNotFoundError:
            devices.append("NVIDIA: Driver não instalado")
        except Exception as e:
            devices.append(f"NVIDIA: Erro ({str(e)})")

        # Etapa 3: Detectar GPUs AMD
        gui_instance.output_queue.put(("device_progress", 75))
        gui_instance.output_queue.put(("device_status", "Detectando GPUs AMD..."))
        try:
            result = subprocess.run(['rocminfo'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and "AMD" in result.stdout:
                devices.append("AMD GPU: ROCm detectado")
            else:
                devices.append("AMD: Não detectado")
        except subprocess.TimeoutExpired:
            devices.append("AMD: Timeout na detecção")
        except FileNotFoundError:
            devices.append("AMD: ROCm não instalado")
        except Exception as e:
            devices.append(f"AMD: Erro ({str(e)})")

        # Etapa 4: Verificar OpenCL (método alternativo mais leve)
        gui_instance.output_queue.put(("device_progress", 90))
        gui_instance.output_queue.put(("device_status", "Detectando dispositivos OpenCL..."))
        try:
            # Tentar detectar via pyopencl se disponível
            import pyopencl as cl
            platforms = cl.get_platforms()
            for platform in platforms:
                devices_cl = platform.get_devices()
                for device in devices_cl:
                    devices.append(f"OpenCL: {device.name} ({platform.name})")
        except ImportError:
            devices.append("OpenCL: Biblioteca não instalada")
        except Exception as e:
            devices.append(f"OpenCL: Erro ({str(e)})")

        # Etapa 5: Finalizar
        gui_instance.output_queue.put(("device_progress", 100))
        gui_instance.output_queue.put(("device_status", "Detecção concluída"))

        if not devices:
            devices.append("Nenhum dispositivo detectado")

        # Atualizar lista na thread principal
        gui_instance.output_queue.put(("device_list", devices))

    except Exception as e:
        gui_instance.output_queue.put(("device_error", f"Erro geral na detecção: {str(e)}"))