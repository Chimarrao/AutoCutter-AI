#!/usr/bin/env python3
"""
Módulo de transcrição para AutoCutter-AI
Contém funções de transcrição de vídeo e geração de legendas
"""

import os
import sys
import threading
import subprocess
import queue
import json
import tempfile
import shutil
from datetime import timedelta

def check_ffmpeg():
    """Verificar se ffmpeg está instalado e disponível"""
    try:
        result = subprocess.run(['ffmpeg', '-version'],
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            # Extrair versão
            version_line = result.stdout.split('\n')[0]
            return True, version_line
        else:
            return False, "FFmpeg não encontrado"
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError) as e:
        return False, f"Erro ao verificar FFmpeg: {str(e)}"

def format_timestamp(seconds):
    """Converter segundos para formato de timestamp SRT (HH:MM:SS,mmm)"""
    td = timedelta(seconds=seconds)
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = td.microseconds // 1000
    return "02d"

def generate_srt(segments):
    """Gerar conteúdo SRT a partir de segmentos do Whisper"""
    srt_content = []
    for i, segment in enumerate(segments, 1):
        start_time = format_timestamp(segment['start'])
        end_time = format_timestamp(segment['end'])
        text = segment['text'].strip()

        srt_content.append(f"{i}")
        srt_content.append(f"{start_time} --> {end_time}")
        srt_content.append(text)
        srt_content.append("")  # Linha em branco

    return "\n".join(srt_content)

def generate_ass(segments, video_width=1920, video_height=1080):
    """Gerar conteúdo ASS a partir de segmentos do Whisper"""
    ass_header = f"""[Script Info]
Title: AutoCutter-AI Transcription
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,2,2,30,30,30,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    ass_events = []
    for segment in segments:
        start_time = format_timestamp(segment['start']).replace(',', '.')
        end_time = format_timestamp(segment['end']).replace(',', '.')
        text = segment['text'].strip()

        ass_events.append(f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}")

    return ass_header + "\n".join(ass_events)

def extract_audio(video_path, output_audio_path):
    """Extrair áudio do vídeo usando ffmpeg"""
    try:
        cmd = [
            'ffmpeg', '-i', video_path,
            '-vn',  # Sem vídeo
            '-acodec', 'pcm_s16le',  # PCM 16-bit
            '-ar', '16000',  # 16kHz sample rate (ideal para Whisper)
            '-ac', '1',  # Mono
            '-y',  # Sobrescrever
            output_audio_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0, result.stderr if result.returncode != 0 else None

    except Exception as e:
        return False, str(e)

def run_whisper_transcription(audio_path, model="base", device="cpu", language=None):
    """Executar transcrição usando Whisper"""
    try:
        import whisper

        # Carregar modelo
        model_obj = whisper.load_model(model, device=device)

        # Configurar opções
        options = {}
        if language:
            options['language'] = language

        # Transcrever
        result = model_obj.transcribe(audio_path, **options)

        return True, result

    except ImportError:
        return False, "Whisper não instalado. Instale com: pip install openai-whisper"
    except Exception as e:
        return False, f"Erro na transcrição: {str(e)}"

def render_video_with_subtitles(video_path, subtitle_path, output_path, quality="1080p 30fps"):
    """Renderizar vídeo com legendas usando ffmpeg"""
    try:
        # Mapear qualidade para configurações ffmpeg
        quality_map = {
            "4K 30fps": ("3840:2160", "30"),
            "1080p 60fps": ("1920:1080", "60"),
            "1080p 30fps": ("1920:1080", "30"),
            "720p 60fps": ("1280:720", "60"),
            "720p 30fps": ("1280:720", "30"),
            "480p 30fps": ("854:480", "30")
        }

        scale, fps = quality_map.get(quality, ("1920:1080", "30"))

        # Detectar formato da legenda
        subtitle_ext = os.path.splitext(subtitle_path)[1].lower()

        if subtitle_ext == '.srt':
            subtitle_filter = f"subtitles='{subtitle_path}':force_style='FontSize=24,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,BorderStyle=1,Outline=2'"
        elif subtitle_ext == '.ass':
            subtitle_filter = f"ass='{subtitle_path}'"
        else:
            return False, "Formato de legenda não suportado. Use .srt ou .ass"

        cmd = [
            'ffmpeg', '-i', video_path,
            '-vf', f"scale={scale},{subtitle_filter}",
            '-r', fps,
            '-c:v', 'libx264',
            '-preset', 'slow',
            '-crf', '18',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-y',
            output_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0, result.stderr if result.returncode != 0 else None

    except Exception as e:
        return False, str(e)

def start_transcription(gui_instance):
    """Iniciar processo de transcrição"""
    # Validar entrada
    if not gui_instance.transcription_video_path:
        gui_instance.output_queue.put(("transcription_error", "Selecione um arquivo de vídeo para transcrição!"))
        return

    if not os.path.exists(gui_instance.transcription_video_path):
        gui_instance.output_queue.put(("transcription_error", "O arquivo de vídeo não existe!"))
        return

    # Verificar ffmpeg
    ffmpeg_ok, ffmpeg_msg = check_ffmpeg()
    if not ffmpeg_ok:
        gui_instance.output_queue.put(("transcription_error", f"FFmpeg não encontrado: {ffmpeg_msg}"))
        return

    # Iniciar thread de transcrição
    thread = threading.Thread(
        target=transcription_thread,
        args=(gui_instance,),
        daemon=True
    )
    thread.start()

def transcription_thread(gui_instance):
    """Thread para processar transcrição"""
    try:
        gui_instance.output_queue.put(("transcription_status", "🔄 Iniciando transcrição..."))
        gui_instance.output_queue.put(("transcription_progress", 5))

        # Extrair áudio
        gui_instance.output_queue.put(("transcription_status", "🎵 Extraindo áudio do vídeo..."))
        gui_instance.output_queue.put(("transcription_progress", 20))

        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio:
            temp_audio_path = temp_audio.name

        success, error = extract_audio(gui_instance.transcription_video_path, temp_audio_path)
        if not success:
            gui_instance.output_queue.put(("transcription_error", f"Erro ao extrair áudio: {error}"))
            return

        gui_instance.output_queue.put(("transcription_progress", 40))

        # Executar Whisper
        model = gui_instance.transcription_model_combo.currentText()
        device = "cuda" if gui_instance.transcription_gpu_check.isChecked() else "cpu"

        gui_instance.output_queue.put(("transcription_status", f"🎤 Transcrevendo com Whisper ({model})..."))
        gui_instance.output_queue.put(("transcription_progress", 60))

        success, result = run_whisper_transcription(temp_audio_path, model=model, device=device)
        if not success:
            gui_instance.output_queue.put(("transcription_error", result))
            return

        gui_instance.output_queue.put(("transcription_progress", 80))

        # Processar resultados
        segments = result['segments']
        full_text = result['text']

        # Salvar segmentos para uso posterior
        gui_instance.transcription_segments = segments
        gui_instance.transcription_text = full_text

        # Atualizar interface
        gui_instance.output_queue.put(("transcription_progress", 100))
        gui_instance.output_queue.put(("transcription_status", "✅ Transcrição concluída!"))
        gui_instance.output_queue.put(("transcription_result", segments))

        # Limpar arquivo temporário
        try:
            os.unlink(temp_audio_path)
        except:
            pass

    except Exception as e:
        gui_instance.output_queue.put(("transcription_error", f"Erro na transcrição: {str(e)}"))

def start_video_render(gui_instance):
    """Iniciar renderização de vídeo com legendas"""
    if not gui_instance.transcription_video_path:
        gui_instance.output_queue.put(("render_error", "Selecione um vídeo para renderizar!"))
        return

    if not hasattr(gui_instance, 'transcription_segments') or not gui_instance.transcription_segments:
        gui_instance.output_queue.put(("render_error", "Execute a transcrição primeiro!"))
        return

    # Verificar ffmpeg
    ffmpeg_ok, ffmpeg_msg = check_ffmpeg()
    if not ffmpeg_ok:
        gui_instance.output_queue.put(("render_error", f"FFmpeg não encontrado: {ffmpeg_msg}"))
        return

    # Iniciar thread de renderização
    thread = threading.Thread(
        target=render_thread,
        args=(gui_instance,),
        daemon=True
    )
    thread.start()

def render_thread(gui_instance):
    """Thread para renderizar vídeo com legendas"""
    try:
        gui_instance.output_queue.put(("render_status", "🎬 Iniciando renderização..."))

        # Criar arquivo de legenda temporário
        with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False, encoding='utf-8') as temp_sub:
            temp_sub_path = temp_sub.name
            srt_content = generate_srt(gui_instance.transcription_segments)
            temp_sub.write(srt_content)

        # Definir caminho de saída
        base_name = os.path.splitext(os.path.basename(gui_instance.transcription_video_path))[0]
        quality = gui_instance.render_quality_combo.currentText().replace(' ', '_')
        output_path = os.path.join("saida", f"{base_name}_com_legendas_{quality}.mp4")

        # Renderizar
        gui_instance.output_queue.put(("render_status", "🎬 Renderizando vídeo com legendas..."))

        success, error = render_video_with_subtitles(
            gui_instance.transcription_video_path,
            temp_sub_path,
            output_path,
            gui_instance.render_quality_combo.currentText()
        )

        # Limpar arquivo temporário
        try:
            os.unlink(temp_sub_path)
        except:
            pass

        if success:
            gui_instance.output_queue.put(("render_status", f"✅ Vídeo renderizado: {output_path}"))
            gui_instance.output_queue.put(("render_success", output_path))
        else:
            gui_instance.output_queue.put(("render_error", f"Erro na renderização: {error}"))

    except Exception as e:
        gui_instance.output_queue.put(("render_error", f"Erro na renderização: {str(e)}"))