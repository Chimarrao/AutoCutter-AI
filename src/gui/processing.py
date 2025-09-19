#!/usr/bin/env python3
import sys
import os
import json
import queue
import threading
import subprocess
import tempfile
import re
import unicodedata
import urllib.parse
import yt_dlp
import requests
import sponsorblock as sb
import io

# força UTF-8 como padrão (apenas se stdout estiver disponível)
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
    """Iniciar processamento de vídeo para geração de clipes"""
    # Verificar se vídeo foi selecionado
    if not gui_instance.video_path or not os.path.exists(gui_instance.video_path):
        gui_instance.output_queue.put(("error", "Por favor, selecione um arquivo de vídeo válido!"))
        return

    # Verificar se pasta de saída existe
    if not os.path.exists(gui_instance.output_dir):
        try:
            os.makedirs(gui_instance.output_dir, exist_ok=True)
        except Exception as e:
            gui_instance.output_queue.put(("error", f"Erro ao criar pasta de saída: {e}"))
            return

    # Verificar se API key foi fornecida
    if not gui_instance.api_key:
        gui_instance.output_queue.put(("error", "Por favor, forneça uma API Key válida!"))
        return

    # Desabilitar botão e mudar aba
    gui_instance.process_btn.setEnabled(False)
    gui_instance.tab_widget.setCurrentIndex(3)  # Mudar para aba de processamento
    gui_instance.progress_bar.setValue(0)
    gui_instance.log_text.clear()
    gui_instance.is_processing = True

    # Iniciar processamento em thread separada
    thread = threading.Thread(target=process_video_thread, args=(gui_instance,), daemon=True)
    thread.start()

def process_video_thread(gui_instance):
    """Thread para processar vídeo e gerar clipes"""
    try:
        gui_instance.output_queue.put(("log", "🚀 Iniciando processamento do vídeo...\n"))
        gui_instance.output_queue.put(("progress", 5))

        # Verificar se ffmpeg está instalado
        try:
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                raise Exception("FFmpeg não encontrado")
        except Exception as e:
            gui_instance.output_queue.put(("error", f"FFmpeg não está instalado ou não é acessível: {e}"))
            return

        gui_instance.output_queue.put(("log", "✅ FFmpeg detectado\n"))
        gui_instance.output_queue.put(("progress", 10))

        # Verificar se whisper está instalado
        try:
            import whisper
            gui_instance.output_queue.put(("log", "✅ Whisper detectado\n"))
        except ImportError:
            gui_instance.output_queue.put(("error", "Whisper não está instalado. Instale com: pip install openai-whisper"))
            return

        gui_instance.output_queue.put(("progress", 15))

        # Carregar modelo Whisper
        gui_instance.output_queue.put(("log", f"🔄 Carregando modelo Whisper '{gui_instance.whisper_model}'...\n"))
        try:
            model = whisper.load_model(gui_instance.whisper_model)
            gui_instance.output_queue.put(("log", "✅ Modelo Whisper carregado\n"))
        except Exception as e:
            gui_instance.output_queue.put(("error", f"Erro ao carregar modelo Whisper: {e}"))
            return

        gui_instance.output_queue.put(("progress", 25))

        # Transcrever vídeo
        gui_instance.output_queue.put(("log", "🎙️ Transcrevendo vídeo...\n"))
        try:
            result = model.transcribe(gui_instance.video_path, language="pt")
            transcription = result["text"]
            segments = result["segments"]
            gui_instance.output_queue.put(("log", "✅ Transcrição concluída\n"))
        except Exception as e:
            gui_instance.output_queue.put(("error", f"Erro na transcrição: {e}"))
            return

        gui_instance.output_queue.put(("progress", 40))

        # Preparar prompt para IA
        gui_instance.output_queue.put(("log", "🤖 Preparando prompt para IA...\n"))

        # Ler arquivo de prompt
        prompt_file = os.path.join(os.path.dirname(__file__), "../../../prompt_corte_youtube.py")
        if os.path.exists(prompt_file):
            try:
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    prompt_content = f.read()
                # Extrair apenas a parte do prompt
                if 'PROMPT_CORTE' in prompt_content:
                    start = prompt_content.find('PROMPT_CORTE = """') + len('PROMPT_CORTE = """')
                    end = prompt_content.find('"""', start)
                    base_prompt = prompt_content[start:end]
                else:
                    base_prompt = "Analise a transcrição e identifique os momentos mais interessantes para criar clipes curtos de até 60 segundos."
            except Exception as e:
                gui_instance.output_queue.put(("error", f"Erro ao ler arquivo de prompt: {e}"))
                return
        else:
            base_prompt = "Analise a transcrição e identifique os momentos mais interessantes para criar clipes curtos de até 60 segundos."

        # Montar prompt completo
        full_prompt = f"""{base_prompt}

Transcrição do vídeo:
{transcription}

Instruções adicionais:
- Gere entre {gui_instance.min_clips} e {gui_instance.max_clips} clipes
- Cada clipe deve ter no máximo {gui_instance.max_segment_duration} segundos
- Foque em momentos interessantes, polêmicos ou de alto engajamento
- Retorne apenas um JSON válido com o formato especificado
"""

        gui_instance.output_queue.put(("progress", 50))

        # Chamar API da OpenAI
        gui_instance.output_queue.put(("log", "🔄 Enviando para IA...\n"))
        try:
            headers = {
                'Authorization': f'Bearer {gui_instance.api_key}',
                'Content-Type': 'application/json'
            }

            data = {
                'model': 'gpt-4',
                'messages': [{'role': 'user', 'content': full_prompt}],
                'temperature': 0.7,
                'max_tokens': 2000
            }

            response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=data, timeout=60)
            response.raise_for_status()

            result = response.json()
            content = result['choices'][0]['message']['content']

            # Extrair JSON da resposta
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_content = content[json_start:json_end]
                clips_data = json.loads(json_content)
            else:
                raise Exception("JSON não encontrado na resposta da IA")

            gui_instance.output_queue.put(("log", "✅ Análise da IA concluída\n"))

        except Exception as e:
            gui_instance.output_queue.put(("error", f"Erro na chamada da API: {e}"))
            return

        gui_instance.output_queue.put(("progress", 70))

        # Processar clipes
        if 'clips' not in clips_data:
            gui_instance.output_queue.put(("error", "Formato de resposta inválido da IA"))
            return

        clips = clips_data['clips']
        gui_instance.output_queue.put(("log", f"🎬 Processando {len(clips)} clipes...\n"))

        for i, clip in enumerate(clips):
            try:
                start_time = clip['start_time']
                end_time = clip['end_time']
                title = clip['title']

                gui_instance.output_queue.put(("log", f"📝 Processando clipe {i+1}/{len(clips)}: {title}\n"))

                # Gerar nome do arquivo
                safe_title = normalize_filename(title)
                output_file = os.path.join(gui_instance.output_dir, f"{safe_title}.mp4")

                # Comando FFmpeg
                cmd = [
                    'ffmpeg', '-y',
                    '-i', gui_instance.video_path,
                    '-ss', str(start_time),
                    '-t', str(end_time - start_time),
                    '-c:v', 'libx264',
                    '-c:a', 'aac',
                    '-preset', 'fast',
                    '-crf', '23',
                    output_file
                ]

                # Executar FFmpeg
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    gui_instance.output_queue.put(("log", f"⚠️ Erro no clipe '{title}': {result.stderr}\n"))
                    continue

                gui_instance.output_queue.put(("log", f"✅ Clipe salvo: {os.path.basename(output_file)}\n"))

                # Atualizar progresso
                progress = 70 + ((i + 1) / len(clips)) * 25
                gui_instance.output_queue.put(("progress", progress))

            except Exception as e:
                gui_instance.output_queue.put(("log", f"⚠️ Erro no clipe {i+1}: {e}\n"))
                continue

        gui_instance.output_queue.put(("progress", 95))

        # Gerar legendas se solicitado
        if gui_instance.captions:
            gui_instance.output_queue.put(("log", "📝 Gerando legendas...\n"))
            # Implementar geração de legendas aqui se necessário

        gui_instance.output_queue.put(("progress", 100))
        gui_instance.output_queue.put(("log", "🎉 Processamento concluído!\n"))
        gui_instance.output_queue.put(("finished", True))

    except Exception as e:
        gui_instance.output_queue.put(("error", f"Erro geral no processamento: {e}"))
        gui_instance.output_queue.put(("finished", False))

    finally:
        gui_instance.is_processing = False
        gui_instance.process_btn.setEnabled(True)

def start_bulk_download(gui_instance):
    """Iniciar download em massa de vídeos"""
    urls_text = gui_instance.bulk_urls_text.toPlainText().strip()

    if not urls_text:
        gui_instance.output_queue.put(("error", "Por favor, adicione URLs para download!"))
        return

    urls = [url.strip() for url in urls_text.split("\n") if url.strip()]

    if not urls:
        gui_instance.output_queue.put(("error", "Nenhuma URL válida encontrada!"))
        return

    if gui_instance.is_downloading:
        gui_instance.output_queue.put(("error", "Já existe um download em andamento!"))
        return

    # Criar pasta de download em massa se não existir
    os.makedirs(gui_instance.bulk_download_dir, exist_ok=True)

    # Iniciar download em thread separada
    gui_instance.is_downloading = True
    gui_instance.bulk_download_btn.setEnabled(False)
    gui_instance.tab_widget.setCurrentIndex(3)  # Mudar para aba de processamento
    gui_instance.bulk_progress.setValue(0)
    gui_instance.bulk_log.clear()

    thread = threading.Thread(target=bulk_download_thread, args=(gui_instance, urls), daemon=True)
    thread.start()

def bulk_download_thread(gui_instance, urls):
    """Thread para download em massa de vídeos"""
    try:
        total_urls = len(urls)
        downloaded = 0
        failed = 0

        gui_instance.output_queue.put(("bulk_log", f"📥 Iniciando download de {total_urls} vídeos...\n"))
        gui_instance.output_queue.put(("bulk_log", f"📁 Pasta de destino: {gui_instance.bulk_download_dir}\n\n"))

        for i, url in enumerate(urls, 1):
            if not is_valid_youtube_url(url):
                gui_instance.output_queue.put(("bulk_log", f"❌ URL inválida: {url}\n"))
                failed += 1
                continue

            gui_instance.output_queue.put(("bulk_status", f"📥 Baixando {i}/{total_urls}: {url[:50]}..."))
            gui_instance.output_queue.put(("bulk_log", f"🔄 Processando {i}/{total_urls}: {url}\n"))

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
                            gui_instance.output_queue.put(("bulk_progress", min(global_progress, 95)))

                            # Atualizar status com informações de download
                            speed = d.get('speed', 0)
                            if speed:
                                speed_mb = speed / 1024 / 1024
                                gui_instance.output_queue.put(("bulk_status", f"📥 Baixando {i}/{total_urls} - {speed_mb:.1f} MB/s"))

                        except Exception as e:
                            gui_instance.output_queue.put(("bulk_log", f"Erro ao processar progresso: {e}\n"))

                    elif d['status'] == 'finished':
                        filename = os.path.basename(d['filename'])
                        # Normalizar o nome do arquivo
                        normalized_filename = normalize_filename(filename)
                        if normalized_filename != filename:
                            old_path = d['filename']
                            new_path = os.path.join(os.path.dirname(old_path), normalized_filename)
                            try:
                                os.rename(old_path, new_path)
                                gui_instance.output_queue.put(("bulk_log", f"📝 Arquivo renomeado: {filename} → {normalized_filename}\n"))
                            except Exception as e:
                                gui_instance.output_queue.put(("bulk_log", f"⚠️ Erro ao renomear arquivo: {e}\n"))

                        gui_instance.output_queue.put(("bulk_log", f"✅ Download concluído: {normalized_filename}\n"))

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

                    gui_instance.output_queue.put(("bulk_log", f"📽️ Título: {title}\n"))
                    gui_instance.output_queue.put(("bulk_log", f"📝 Canal: {uploader}\n"))
                    gui_instance.output_queue.put(("bulk_log", f"⏱️ Duração: {duration // 60}:{duration % 60:02d}\n"))

                    # Verificar se já existe
                    normalized_title = normalize_filename(title)
                    ext = 'mp3' if quality == "audio" else 'mp4'
                    expected_filename = os.path.join(gui_instance.bulk_download_dir, f"{normalized_title}.{ext}")

                    if os.path.exists(expected_filename):
                        gui_instance.output_queue.put(("bulk_log", f"📁 Arquivo já existe, pulando: {normalized_title}.{ext}\n"))
                        downloaded += 1
                    else:
                        # Baixar o vídeo
                        ydl.download([url])
                        downloaded += 1

                    gui_instance.output_queue.put(("bulk_log", f"✅ Processado {i}/{total_urls}\n\n"))

            except Exception as e:
                gui_instance.output_queue.put(("bulk_log", f"❌ Erro ao baixar {url}: {str(e)}\n\n"))
                failed += 1

            # Atualizar progresso global
            global_progress = (i / total_urls) * 100
            gui_instance.output_queue.put(("bulk_progress", global_progress))

        # Finalizar
        gui_instance.output_queue.put(("bulk_progress", 100))
        gui_instance.output_queue.put(("bulk_status", f"✅ Download em massa concluído!"))
        gui_instance.output_queue.put(("bulk_log", f"\n🎉 Download em massa finalizado!\n"))
        gui_instance.output_queue.put(("bulk_log", f"✅ Sucessos: {downloaded}\n"))
        gui_instance.output_queue.put(("bulk_log", f"❌ Falhas: {failed}\n"))
        gui_instance.output_queue.put(("bulk_log", f"📁 Pasta: {gui_instance.bulk_download_dir}\n"))

        gui_instance.output_queue.put(("bulk_download_finished", True))

    except Exception as e:
        error_msg = str(e)
        gui_instance.output_queue.put(("bulk_log", f"❌ Erro no download em massa: {error_msg}\n"))
        gui_instance.output_queue.put(("bulk_status", "❌ Erro no download em massa"))
        gui_instance.output_queue.put(("bulk_download_finished", False))

def detect_devices_thread(gui_instance):
    """Thread para detectar dispositivos com barra de progresso usando métodos leves"""
    try:
        devices = []

        # Etapa 1: Detectar CPUs
        gui_instance.output_queue.put(("device_progress", 20))
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

        # Etapa 2: Detectar GPUs NVIDIA (sem torch)
        gui_instance.output_queue.put(("device_progress", 40))
        gui_instance.output_queue.put(("device_status", "Detectando GPUs NVIDIA..."))
        try:
            # Usar nvidia-smi diretamente
            result = subprocess.run(['nvidia-smi', '--query-gpu=name', '--format=csv,noheader,nounits'],
                                  capture_output=True, text=True, timeout=3)
            if result.returncode == 0 and result.stdout.strip():
                gpu_names = result.stdout.strip().split('\n')
                for i, name in enumerate(gpu_names):
                    if name.strip():
                        devices.append(f"NVIDIA GPU {i}: {name.strip()}")
            else:
                devices.append("NVIDIA: Não detectado")
        except subprocess.TimeoutExpired:
            devices.append("NVIDIA: Timeout na detecção")
        except FileNotFoundError:
            devices.append("NVIDIA: Driver não instalado")
        except Exception as e:
            devices.append(f"NVIDIA: Erro ({str(e)})")

        # Etapa 3: Detectar GPUs AMD/Intel via OpenCL
        gui_instance.output_queue.put(("device_progress", 60))
        gui_instance.output_queue.put(("device_status", "Detectando GPUs AMD/Intel via OpenCL..."))
        try:
            import pyopencl as cl
            platforms = cl.get_platforms()
            for platform in platforms:
                devices_cl = platform.get_devices()
                for device in devices_cl:
                    device_type = "GPU" if device.type == cl.device_type.GPU else "CPU"
                    devices.append(f"OpenCL {device_type}: {device.name} ({platform.name})")
            if not any("OpenCL" in d for d in devices):
                devices.append("OpenCL: Plataformas detectadas mas sem dispositivos GPU")
        except ImportError:
            devices.append("OpenCL: pyopencl não instalado")
        except Exception as e:
            devices.append(f"OpenCL: Erro ({str(e)})")

        # Etapa 4: Detectar VAAPI (Linux)
        gui_instance.output_queue.put(("device_progress", 80))
        gui_instance.output_queue.put(("device_status", "Detectando VAAPI..."))
        try:
            if os.name == 'posix':  # Linux/Unix
                result = subprocess.run(['vainfo'], capture_output=True, text=True, timeout=3)
                if result.returncode == 0 and "VAAPI" in result.stdout:
                    devices.append("VAAPI: Suporte detectado")
                else:
                    devices.append("VAAPI: Não detectado")
            else:
                devices.append("VAAPI: Não aplicável (não Linux)")
        except subprocess.TimeoutExpired:
            devices.append("VAAPI: Timeout na detecção")
        except FileNotFoundError:
            devices.append("VAAPI: vainfo não instalado")
        except Exception as e:
            devices.append(f"VAAPI: Erro ({str(e)})")

        # Etapa 5: Finalizar
        gui_instance.output_queue.put(("device_progress", 100))
        gui_instance.output_queue.put(("device_status", "Detecção concluída"))

        if not devices:
            devices.append("Nenhum dispositivo detectado")

        # Atualizar lista na thread principal
        gui_instance.output_queue.put(("device_list", devices))

    except Exception as e:
        gui_instance.output_queue.put(("device_error", f"Erro geral na detecção: {str(e)}"))