#!/usr/bin/env python3
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import threading
import os
import json
import queue
import tempfile
import re
import yt_dlp
import urllib.parse
import unicodedata
import requests
import sponsorblock as sb
import io
import sys

# força UTF-8 como padrão
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
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


class ClipGeneratorGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🎬 Gerador de Clipes com IA")
        self.root.geometry("1280x900")
        self.root.resizable(True, True)
        self.root.configure(bg='#2b2b2b')

        # Arquivo de configuração
        self.config_file = os.path.join(os.path.dirname(__file__), 'user_config.json')

        # Carregar configurações salvas
        self.load_config()

        # Variáveis para a aba básica (geração de clipes)
        self.video_path = tk.StringVar()
        self.youtube_url = tk.StringVar()
        self.output_dir = tk.StringVar(value="output_folder")
        self.min_clips = tk.IntVar(value=3)
        self.max_clips = tk.IntVar(value=8)
        self.whisper_model = tk.StringVar(value="base")
        self.api_key = tk.StringVar(value=self.saved_api_key)
        self.captions = tk.BooleanVar(value=True)
        self.no_review = tk.BooleanVar(value=True)
        self.max_segment_duration = tk.IntVar(value=30)
        self.temp_dir = tk.StringVar(value=os.path.join(os.path.dirname(__file__), "temp"))
        self.downloads_dir = tk.StringVar(value=os.path.join(os.path.dirname(__file__), "downloads"))
        self.bulk_download_dir = tk.StringVar(value=os.path.join(os.path.dirname(__file__), "bulk_download"))
        self.is_downloading = False
        self.mode = tk.StringVar(value="clips")
        self.bulk_urls = tk.StringVar()

        # Variáveis separadas para o Vídeo Maker
        self.vm_video_path = tk.StringVar()
        self.vm_personagens = tk.StringVar()
        self.vm_texto_thumb = tk.StringVar()
        self.vm_sponsor_block = tk.BooleanVar(value=True)
        self.vm_black_bars = tk.BooleanVar(value=True)
        self.vm_black_bars_height = tk.IntVar(value=170)
        self.vm_cut_last_seconds = tk.BooleanVar(value=True)
        self.vm_cut_seconds = tk.IntVar(value=20)
        self.vm_quality = tk.StringVar(value="1080p 30fps")
        self.vm_video_title = None
        self.vm_video_id = None
        self.vm_is_processing = False

        # Fila para comunicação entre threads
        self.output_queue = queue.Queue()
        self.process = None
        self.is_processing = False

        self.setup_ui()
        self.check_queue()

    def load_config(self):
        """Carregar configurações do usuário"""
        self.saved_api_key = ""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.saved_api_key = config.get('api_key', '')
        except Exception as e:
            print(f"Erro ao carregar configurações: {e}")

    def save_config(self):
        """Salvar configurações do usuário"""
        try:
            config = {
                'api_key': self.api_key.get()
            }
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Erro ao salvar configurações: {e}")

    def setup_ui(self):
        # Configurar style
        style = ttk.Style()
        style.theme_use('clam')

        # Frame principal
        main_frame = tk.Frame(self.root, bg='#2b2b2b')
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Título
        title_label = tk.Label(
            main_frame,
            text="🎬 Gerador de Clipes com IA",
            font=("Arial", 24, "bold"),
            bg='#2b2b2b',
            fg='white'
        )
        title_label.pack(pady=(20, 10))

        # Subtitle
        subtitle_label = tk.Label(
            main_frame,
            text="Transforme seus vídeos em clipes curtos automaticamente",
            font=("Arial", 12),
            bg='#2b2b2b',
            fg='#cccccc'
        )
        subtitle_label.pack(pady=(0, 30))

        # Notebook para as abas
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill="both", expand=True, padx=20, pady=20)

        # Criar as abas
        self.setup_basic_tab()
        self.setup_bulk_download_tab()
        self.setup_advanced_tab()
        self.setup_processing_tab()
        self.setup_video_maker_tab()

    def setup_basic_tab(self):
        # Frame da aba básica
        basic_frame = tk.Frame(self.notebook, bg='#3b3b3b')
        self.notebook.add(basic_frame, text="📁 Básico")

        # Canvas e scrollbar para scroll
        canvas = tk.Canvas(basic_frame, bg='#3b3b3b', highlightthickness=0)
        scrollbar = ttk.Scrollbar(basic_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#3b3b3b')

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Seleção de vídeo
        video_frame = tk.LabelFrame(scrollable_frame, text="📹 Arquivo de Vídeo",
                                   font=("Arial", 12, "bold"), bg='#3b3b3b', fg='white')
        video_frame.pack(fill="x", padx=10, pady=10)

        video_input_frame = tk.Frame(video_frame, bg='#3b3b3b')
        video_input_frame.pack(fill="x", padx=20, pady=20)

        self.video_entry = tk.Entry(
            video_input_frame,
            textvariable=self.video_path,
            font=("Arial", 12),
            width=50
        )
        self.video_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        tk.Button(
            video_input_frame,
            text="📂 Navegar",
            command=self.browse_video,
            width=12,
            bg='#555555',
            fg='white'
        ).pack(side="right")

        # URL do YouTube
        youtube_frame = tk.LabelFrame(scrollable_frame, text="🔗 URL do YouTube",
                                     font=("Arial", 12, "bold"), bg='#3b3b3b', fg='white')
        youtube_frame.pack(fill="x", padx=10, pady=10)

        youtube_input_frame = tk.Frame(youtube_frame, bg='#3b3b3b')
        youtube_input_frame.pack(fill="x", padx=20, pady=20)

        self.youtube_entry = tk.Entry(
            youtube_input_frame,
            textvariable=self.youtube_url,
            font=("Arial", 12),
            width=50
        )
        self.youtube_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        tk.Button(
            youtube_input_frame,
            text="📥 Baixar",
            command=self.download_youtube_video,
            width=12,
            bg='#555555',
            fg='white'
        ).pack(side="right")

        # Pasta de saída
        output_frame = tk.LabelFrame(scrollable_frame, text="📁 Pasta de Saída",
                                    font=("Arial", 12, "bold"), bg='#3b3b3b', fg='white')
        output_frame.pack(fill="x", padx=10, pady=10)

        output_input_frame = tk.Frame(output_frame, bg='#3b3b3b')
        output_input_frame.pack(fill="x", padx=20, pady=20)

        self.output_entry = tk.Entry(
            output_input_frame,
            textvariable=self.output_dir,
            font=("Arial", 12),
            width=50
        )
        self.output_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        tk.Button(
            output_input_frame,
            text="📂 Navegar",
            command=self.browse_output,
            width=12,
            bg='#555555',
            fg='white'
        ).pack(side="right")

        # Número de clipes
        clips_frame = tk.LabelFrame(scrollable_frame, text="🎯 Quantidade de Clipes",
                                   font=("Arial", 12, "bold"), bg='#3b3b3b', fg='white')
        clips_frame.pack(fill="x", padx=10, pady=10)

        clips_config_frame = tk.Frame(clips_frame, bg='#3b3b3b')
        clips_config_frame.pack(fill="x", padx=20, pady=20)

        # Min clips
        min_frame = tk.Frame(clips_config_frame, bg='#3b3b3b')
        min_frame.pack(side="left", fill="x", expand=True, padx=(0, 10))

        tk.Label(min_frame, text="Mínimo:", font=("Arial", 12), bg='#3b3b3b', fg='white').pack(pady=(10, 5))
        self.min_spinbox = tk.Spinbox(min_frame, textvariable=self.min_clips, from_=1, to=20, width=10, justify="center")
        self.min_spinbox.pack(pady=(0, 10))

        # Max clips
        max_frame = tk.Frame(clips_config_frame, bg='#3b3b3b')
        max_frame.pack(side="right", fill="x", expand=True, padx=(10, 0))

        tk.Label(max_frame, text="Máximo:", font=("Arial", 12), bg='#3b3b3b', fg='white').pack(pady=(10, 5))
        self.max_spinbox = tk.Spinbox(max_frame, textvariable=self.max_clips, from_=1, to=50, width=10, justify="center")
        self.max_spinbox.pack(pady=(0, 10))

        clips_frame_2 = tk.LabelFrame(scrollable_frame, text="🎯 Processar",
                                           font=("Arial", 12, "bold"), bg='#3b3b3b', fg='white')
        clips_frame_2.pack(fill="x", padx=10, pady=10)

        clips_config_frame_2 = tk.Frame(clips_frame_2, bg='#3b3b3b')
        clips_config_frame_2.pack(fill="x", padx=20, pady=20)

        # Frame de botões
        button_frame = tk.Frame(clips_config_frame_2, bg='#2b2b2b')
        button_frame.pack(fill="x", padx=20, pady=20)

        # Botão processar
        self.process_button = tk.Button(
            button_frame,
            text="🚀 Processar Vídeo",
            command=self.start_processing,
            font=("Arial", 14, "bold"),
            height=2,
            width=20,
            bg='#4CAF50',
            fg='white',
            activebackground='#45a049'
        )
        self.process_button.pack(side="left", padx=10, pady=10)

        # Botão parar
        self.stop_button = tk.Button(
            button_frame,
            text="⏹️ Parar",
            command=self.stop_processing,
            state="disabled",
            font=("Arial", 14, "bold"),
            height=2,
            width=15,
            bg='#f44336',
            fg='white',
            activebackground='#da190b'
        )
        self.stop_button.pack(side="right", padx=10, pady=10)

    def setup_bulk_download_tab(self):
        # Frame da aba de download em massa
        bulk_frame = tk.Frame(self.notebook, bg='#3b3b3b')
        self.notebook.add(bulk_frame, text="📥 Download em Massa")

        # Canvas e scrollbar para scroll
        canvas = tk.Canvas(bulk_frame, bg='#3b3b3b', highlightthickness=0)
        scrollbar = ttk.Scrollbar(bulk_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#3b3b3b')

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Título da seção
        tk.Label(
            scrollable_frame,
            text="📥 Download em Massa de Vídeos",
            font=("Arial", 16, "bold"),
            bg='#3b3b3b',
            fg='white'
        ).pack(pady=(10, 20))

        # Pasta de destino para downloads em massa
        bulk_folder_frame = tk.LabelFrame(scrollable_frame, text="📁 Pasta de Destino",
                                         font=("Arial", 12, "bold"), bg='#3b3b3b', fg='white')
        bulk_folder_frame.pack(fill="x", padx=10, pady=10)

        bulk_folder_input_frame = tk.Frame(bulk_folder_frame, bg='#3b3b3b')
        bulk_folder_input_frame.pack(fill="x", padx=20, pady=20)

        self.bulk_folder_entry = tk.Entry(
            bulk_folder_input_frame,
            textvariable=self.bulk_download_dir,
            font=("Arial", 12),
            width=50
        )
        self.bulk_folder_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        tk.Button(
            bulk_folder_input_frame,
            text="📂 Navegar",
            command=self.browse_bulk_folder,
            width=12,
            bg='#555555',
            fg='white'
        ).pack(side="right")

        # Lista de URLs
        urls_frame = tk.LabelFrame(scrollable_frame, text="🔗 URLs do YouTube",
                                  font=("Arial", 12, "bold"), bg='#3b3b3b', fg='white')
        urls_frame.pack(fill="both", expand=True, padx=10, pady=10)

        tk.Label(
            urls_frame,
            text="Cole as URLs do YouTube, uma por linha:",
            font=("Arial", 11),
            bg='#3b3b3b',
            fg='#cccccc'
        ).pack(anchor="w", padx=20, pady=(20, 10))

        # TextBox para múltiplas URLs
        self.bulk_urls_text = tk.Text(
            urls_frame,
            height=10,
            font=("Consolas", 10),
            wrap=tk.WORD
        )
        self.bulk_urls_text.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # Frame para botões
        bulk_buttons_frame = tk.Frame(urls_frame, bg='#3b3b3b')
        bulk_buttons_frame.pack(fill="x", padx=20, pady=(0, 20))

        # Botão para limpar URLs
        tk.Button(
            bulk_buttons_frame,
            text="🗑️ Limpar",
            command=self.clear_bulk_urls,
            width=12,
            bg='#555555',
            fg='white'
        ).pack(side="left", padx=(0, 10))

        # Botão para validar URLs
        tk.Button(
            bulk_buttons_frame,
            text="✅ Validar URLs",
            command=self.validate_bulk_urls,
            width=15,
            bg='#555555',
            fg='white'
        ).pack(side="left", padx=10)

        # Botão para iniciar download em massa
        self.bulk_download_button = tk.Button(
            bulk_buttons_frame,
            text="📥 Baixar Todos",
            command=self.start_bulk_download,
            width=15,
            bg='#4CAF50',
            fg='white'
        )
        self.bulk_download_button.pack(side="right")

        # Opções de download
        options_frame = tk.LabelFrame(scrollable_frame, text="⚙️ Opções de Download",
                                     font=("Arial", 12, "bold"), bg='#3b3b3b', fg='white')
        options_frame.pack(fill="x", padx=10, pady=10)

        # Checkbox para baixar thumbnails
        self.download_thumbnails = tk.BooleanVar(value=True)
        self.thumbnails_checkbox = tk.Checkbutton(
            options_frame,
            text="Baixar thumbnails dos vídeos",
            variable=self.download_thumbnails,
            font=("Arial", 11),
            bg='#3b3b3b',
            fg='white',
            selectcolor='#3b3b3b'
        )
        self.thumbnails_checkbox.pack(anchor="w", padx=20, pady=(20, 10))

        # Formato das thumbnails
        self.thumbnail_format = tk.StringVar(value="jpg")
        thumbnail_format_frame = tk.Frame(options_frame, bg='#3b3b3b')
        thumbnail_format_frame.pack(fill="x", padx=20, pady=(0, 10))

        tk.Label(
            thumbnail_format_frame,
            text="Formato das thumbnails:",
            font=("Arial", 10),
            bg='#3b3b3b',
            fg='white'
        ).pack(side="left", padx=(0, 10))

        self.thumbnail_format_combo = ttk.Combobox(
            thumbnail_format_frame,
            values=["jpg", "png"],
            textvariable=self.thumbnail_format,
            state="readonly",
            width=10,
            font=("Arial", 10)
        )
        self.thumbnail_format_combo.pack(side="left")

        # Checkbox para baixar apenas áudio
        self.audio_only = tk.BooleanVar(value=False)
        self.audio_only_checkbox = tk.Checkbutton(
            options_frame,
            text="Baixar apenas áudio (MP3)",
            variable=self.audio_only,
            font=("Arial", 11),
            bg='#3b3b3b',
            fg='white',
            selectcolor='#3b3b3b'
        )
        self.audio_only_checkbox.pack(anchor="w", padx=20, pady=(0, 20))

    def setup_advanced_tab(self):
        # Frame da aba avançada
        advanced_frame = tk.Frame(self.notebook, bg='#3b3b3b')
        self.notebook.add(advanced_frame, text="⚙️ Avançado")

        # Canvas e scrollbar para scroll
        canvas = tk.Canvas(advanced_frame, bg='#3b3b3b', highlightthickness=0)
        scrollbar = ttk.Scrollbar(advanced_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#3b3b3b')

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Modelo Whisper
        whisper_frame = tk.LabelFrame(scrollable_frame, text="Modelo Whisper",
                                     font=("Arial", 12, "bold"), bg='#3b3b3b', fg='white')
        whisper_frame.pack(fill="x", padx=10, pady=10)

        self.whisper_combo = ttk.Combobox(
            whisper_frame,
            values=["tiny", "base", "small", "medium", "large"],
            textvariable=self.whisper_model,
            state="readonly",
            font=("Arial", 12)
        )
        self.whisper_combo.pack(fill="x", padx=20, pady=20)

        # API Key
        api_frame = tk.LabelFrame(scrollable_frame, text="Chave API do Google Gemini",
                                 font=("Arial", 12, "bold"), bg='#3b3b3b', fg='white')
        api_frame.pack(fill="x", padx=10, pady=10)

        self.api_entry = tk.Entry(
            api_frame,
            textvariable=self.api_key,
            show="*",
            font=("Arial", 12)
        )
        self.api_entry.pack(fill="x", padx=20, pady=20)

        # Opções
        options_frame = tk.LabelFrame(scrollable_frame, text="Opções",
                                     font=("Arial", 12, "bold"), bg='#3b3b3b', fg='white')
        options_frame.pack(fill="x", padx=10, pady=10)

        # Checkbox para não revisar
        self.no_review_checkbox = tk.Checkbutton(
            options_frame,
            text="Processar sem revisão manual",
            variable=self.no_review,
            font=("Arial", 11),
            bg='#3b3b3b',
            fg='white',
            selectcolor='#3b3b3b'
        )
        self.no_review_checkbox.pack(anchor="w", padx=20, pady=20)

        # Duração máxima do segmento
        duration_frame = tk.LabelFrame(scrollable_frame, text="Duração Máxima do Segmento",
                                      font=("Arial", 12, "bold"), bg='#3b3b3b', fg='white')
        duration_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(
            duration_frame,
            text="Duração máxima de cada segmento em minutos:",
            font=("Arial", 11),
            bg='#3b3b3b',
            fg='white'
        ).pack(anchor="w", padx=20, pady=(20, 10))

        self.duration_spinbox = tk.Spinbox(
            duration_frame,
            textvariable=self.max_segment_duration,
            from_=1,
            to=120,
            width=10,
            justify="center"
        )
        self.duration_spinbox.pack(anchor="w", padx=20, pady=(0, 20))

        # Pasta temporária
        temp_frame = tk.LabelFrame(scrollable_frame, text="Pasta Temporária",
                                  font=("Arial", 12, "bold"), bg='#3b3b3b', fg='white')
        temp_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(
            temp_frame,
            text="Pasta onde os segmentos de vídeo serão armazenados temporariamente:",
            font=("Arial", 11),
            bg='#3b3b3b',
            fg='white'
        ).pack(anchor="w", padx=20, pady=(20, 10))

        temp_input_frame = tk.Frame(temp_frame, bg='#3b3b3b')
        temp_input_frame.pack(fill="x", padx=20, pady=(0, 20))

        self.temp_entry = tk.Entry(
            temp_input_frame,
            textvariable=self.temp_dir,
            font=("Arial", 12)
        )
        self.temp_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        tk.Button(
            temp_input_frame,
            text="Navegar",
            command=self.browse_temp,
            width=12,
            bg='#555555',
            fg='white'
        ).pack(side="right")

        # Modo de Processamento
        mode_frame = tk.LabelFrame(scrollable_frame, text="Modo de Processamento",
                                  font=("Arial", 12, "bold"), bg='#3b3b3b', fg='white')
        mode_frame.pack(fill="x", padx=10, pady=10)

        self.mode_combo = ttk.Combobox(
            mode_frame,
            values=["clips", "summary"],
            textvariable=self.mode,
            state="readonly",
            font=("Arial", 12)
        )
        self.mode_combo.pack(fill="x", padx=20, pady=20)

    def setup_processing_tab(self):
        # Frame da aba de processamento
        processing_frame = tk.Frame(self.notebook, bg='#3b3b3b')
        self.notebook.add(processing_frame, text="⚡ Processamento")

        # Status
        status_frame = tk.LabelFrame(processing_frame, text="📊 Status",
                                    font=("Arial", 12, "bold"), bg='#3b3b3b', fg='white')
        status_frame.pack(fill="x", padx=20, pady=20)

        self.status_label = tk.Label(
            status_frame,
            text="Aguardando...",
            font=("Arial", 12),
            anchor="w",
            bg='#3b3b3b',
            fg='white'
        )
        self.status_label.pack(fill="x", padx=20, pady=20)

        # Barra de progresso
        progress_frame = tk.LabelFrame(processing_frame, text="📈 Progresso",
                                      font=("Arial", 12, "bold"), bg='#3b3b3b', fg='white')
        progress_frame.pack(fill="x", padx=20, pady=(0, 20))

        self.progress_bar = ttk.Progressbar(progress_frame, length=400, mode='determinate')
        self.progress_bar.pack(fill="x", padx=20, pady=20)

        # Log de saída
        log_frame = tk.LabelFrame(processing_frame, text="📝 Log de Processamento",
                                 font=("Arial", 12, "bold"), bg='#3b3b3b', fg='white')
        log_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # Text widget para o log
        self.log_text = tk.Text(
            log_frame,
            height=15,
            font=("Consolas", 10),
            wrap=tk.WORD
        )
        self.log_text.pack(fill="both", expand=True, padx=20, pady=20)

    def setup_video_maker_tab(self):
        # Frame da aba Vídeo Maker
        vm_frame = tk.Frame(self.notebook, bg='#3b3b3b')
        self.notebook.add(vm_frame, text="🎬 Vídeo Maker")

        # Canvas e scrollbar para scroll
        canvas = tk.Canvas(vm_frame, bg='#3b3b3b', highlightthickness=0)
        scrollbar = ttk.Scrollbar(vm_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#3b3b3b')

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Título da seção
        tk.Label(
            scrollable_frame,
            text="🎬 Criação de Vídeos",
            font=("Arial", 16, "bold"),
            bg='#3b3b3b',
            fg='white'
        ).pack(pady=(10, 20))

        # Seleção de vídeo separada para o Video Maker
        video_frame = tk.LabelFrame(scrollable_frame, text="📹 Arquivo de Vídeo",
                                   font=("Arial", 12, "bold"), bg='#3b3b3b', fg='white')
        video_frame.pack(fill="x", padx=10, pady=10)

        video_input_frame = tk.Frame(video_frame, bg='#3b3b3b')
        video_input_frame.pack(fill="x", padx=20, pady=20)

        self.vm_video_entry = tk.Entry(
            video_input_frame,
            textvariable=self.vm_video_path,
            font=("Arial", 12),
            width=50
        )
        self.vm_video_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        tk.Button(
            video_input_frame,
            text="📂 Navegar",
            command=self.browse_vm_video,
            width=12,
            bg='#555555',
            fg='white'
        ).pack(side="right")

        # Personagens
        personagens_frame = tk.LabelFrame(scrollable_frame, text="👤 Personagens",
                                         font=("Arial", 12, "bold"), bg='#3b3b3b', fg='white')
        personagens_frame.pack(fill="x", padx=10, pady=10)

        self.personagens_entry = tk.Entry(
            personagens_frame,
            textvariable=self.vm_personagens,
            font=("Arial", 12)
        )
        self.personagens_entry.pack(fill="x", padx=20, pady=20)

        # Texto para Thumbnail
        thumb_frame = tk.LabelFrame(scrollable_frame, text="🖼️ Texto para Thumbnail",
                                   font=("Arial", 12, "bold"), bg='#3b3b3b', fg='white')
        thumb_frame.pack(fill="x", padx=10, pady=10)

        self.texto_thumb_entry = tk.Entry(
            thumb_frame,
            textvariable=self.vm_texto_thumb,
            font=("Arial", 12)
        )
        self.texto_thumb_entry.pack(fill="x", padx=20, pady=20)

        # Opções de Edição
        edit_options_frame = tk.LabelFrame(scrollable_frame, text="✂️ Opções de Edição",
                                          font=("Arial", 12, "bold"), bg='#3b3b3b', fg='white')
        edit_options_frame.pack(fill="x", padx=10, pady=10)

        # Sponsor Block
        self.sponsor_block_checkbox = tk.Checkbutton(
            edit_options_frame,
            text="Adicionar Sponsor Block",
            variable=self.vm_sponsor_block,
            font=("Arial", 11),
            bg='#3b3b3b',
            fg='white',
            selectcolor='#3b3b3b'
        )
        self.sponsor_block_checkbox.pack(anchor="w", padx=20, pady=(20, 10))

        # Black Bars
        self.black_bars_checkbox = tk.Checkbutton(
            edit_options_frame,
            text="Adicionar Black Bars",
            variable=self.vm_black_bars,
            font=("Arial", 11),
            bg='#3b3b3b',
            fg='white',
            selectcolor='#3b3b3b'
        )
        self.black_bars_checkbox.pack(anchor="w", padx=20, pady=(0, 10))

        tk.Label(
            edit_options_frame,
            text="Altura das Black Bars (px):",
            font=("Arial", 11),
            bg='#3b3b3b',
            fg='white'
        ).pack(anchor="w", padx=20, pady=(10, 5))

        self.black_bars_height_spinbox = tk.Spinbox(
            edit_options_frame,
            textvariable=self.vm_black_bars_height,
            from_=50,
            to=500,
            width=10,
            justify="center"
        )
        self.black_bars_height_spinbox.pack(anchor="w", padx=20, pady=(0, 20))

        # Cortar Últimos Segundos
        self.cut_last_seconds_checkbox = tk.Checkbutton(
            edit_options_frame,
            text="Cortar últimos segundos do vídeo",
            variable=self.vm_cut_last_seconds,
            font=("Arial", 11),
            bg='#3b3b3b',
            fg='white',
            selectcolor='#3b3b3b'
        )
        self.cut_last_seconds_checkbox.pack(anchor="w", padx=20, pady=(0, 10))

        tk.Label(
            edit_options_frame,
            text="Segundos a serem cortados:",
            font=("Arial", 11),
            bg='#3b3b3b',
            fg='white'
        ).pack(anchor="w", padx=20, pady=(10, 5))

        self.cut_seconds_spinbox = tk.Spinbox(
            edit_options_frame,
            textvariable=self.vm_cut_seconds,
            from_=1,
            to=300,
            width=10,
            justify="center"
        )
        self.cut_seconds_spinbox.pack(anchor="w", padx=20, pady=(0, 20))

        # Qualidade do Vídeo
        qualidade_frame = tk.LabelFrame(scrollable_frame, text="📺 Qualidade do Vídeo",
                                       font=("Arial", 12, "bold"), bg='#3b3b3b', fg='white')
        qualidade_frame.pack(fill="x", padx=10, pady=10)

        self.qualidade_combo = ttk.Combobox(
            qualidade_frame,
            values=["1080p 30fps", "720p 30fps", "480p 30fps"],
            textvariable=self.vm_quality,
            state="readonly",
            font=("Arial", 12)
        )
        self.qualidade_combo.pack(fill="x", padx=20, pady=20)

        # Texto para Prompt
        prompt_frame = tk.LabelFrame(scrollable_frame, text="📝 Prompt Gerado",
                                    font=("Arial", 12, "bold"), bg='#3b3b3b', fg='white')
        prompt_frame.pack(fill="x", padx=10, pady=10)

        self.text_prompt = tk.Text(
            prompt_frame,
            height=8,
            font=("Arial", 11),
            wrap=tk.WORD
        )
        self.text_prompt.pack(fill="both", expand=True, padx=20, pady=(20, 10))

        tk.Button(
            prompt_frame,
            text="📋 Copiar Prompt",
            command=self.copiar_prompt,
            width=15,
            bg='#555555',
            fg='white'
        ).pack(anchor="e", padx=20, pady=(0, 20))

        # Frame de botões para o Vídeo Maker
        vm_button_frame = tk.Frame(scrollable_frame, bg='#3b3b3b')
        vm_button_frame.pack(fill="x", padx=10, pady=10)

        # Botão gerar prompt para thumbnail
        tk.Button(
            vm_button_frame,
            text="🖼️ Gerar Prompt Thumbnail",
            command=self.gerar_prompt_thumbnail,
            width=20,
            height=2,
            bg='#555555',
            fg='white'
        ).pack(side="left", padx=10, pady=10)

        # Botão gerar vídeo
        self.gerar_video_button = tk.Button(
            vm_button_frame,
            text="🎬 Gerar Vídeo",
            command=self.gerar_video,
            font=("Arial", 12, "bold"),
            height=2,
            width=20,
            bg='#4CAF50',
            fg='white'
        )
        self.gerar_video_button.pack(side="right", padx=10, pady=10)

    def is_valid_youtube_url(self, url):
        """Validar se a URL é válida do YouTube"""
        try:
            parsed_url = urllib.parse.urlparse(url)
            if parsed_url.netloc in ['www.youtube.com', 'youtube.com', 'youtu.be', 'm.youtube.com']:
                return True
            return False
        except:
            return False

    def download_youtube_video(self):
        """Baixar vídeo do YouTube usando yt-dlp"""
        url = self.youtube_url.get().strip()

        if not url:
            messagebox.showerror("Erro", "Por favor, insira uma URL do YouTube!")
            return

        if not self.is_valid_youtube_url(url):
            messagebox.showerror("Erro", "URL inválida! Por favor, insira uma URL válida do YouTube.")
            return

        if self.is_downloading:
            messagebox.showwarning("Aviso", "Já existe um download em andamento!")
            return

        # Criar pasta de downloads se não existir
        os.makedirs(self.downloads_dir.get(), exist_ok=True)

        # Iniciar download em thread separada
        self.is_downloading = True
        self.notebook.select(3)  # Mudar para aba de processamento
        self.status_label.configure(text="🔄 Iniciando download do YouTube...")
        self.progress_bar['value'] = 0
        self.log_text.delete("1.0", "end")

        thread = threading.Thread(target=self.download_youtube_video_thread, args=(url,), daemon=True)
        thread.start()

    def download_youtube_video_thread(self, url):
        """Thread para download do vídeo do YouTube"""
        try:
            def progress_hook(d):
                if d['status'] == 'downloading':
                    try:
                        # Calcular progresso baseado no tamanho do arquivo
                        if 'total_bytes' in d and d['total_bytes']:
                            percent = (d['downloaded_bytes'] / d['total_bytes']) * 100
                            self.output_queue.put(("progress", min(percent, 95)))
                        elif 'total_bytes_estimate' in d and d['total_bytes_estimate']:
                            percent = (d['downloaded_bytes'] / d['total_bytes_estimate']) * 100
                            self.output_queue.put(("progress", min(percent, 95)))

                        # Atualizar status com informações de download
                        speed = d.get('speed', 0)
                        if speed:
                            speed_mb = speed / 1024 / 1024
                            self.output_queue.put(("status", f"📥 Baixando... {speed_mb:.1f} MB/s"))
                        else:
                            self.output_queue.put(("status", "📥 Baixando..."))

                        # Log detalhado
                        if 'filename' in d:
                            filename = os.path.basename(d['filename'])
                            self.output_queue.put(("log", f"Baixando: {filename}\n"))

                    except Exception as e:
                        self.output_queue.put(("log", f"Erro ao processar progresso: {e}\n"))

                elif d['status'] == 'finished':
                    self.output_queue.put(("progress", 100))
                    self.output_queue.put(("status", "✅ Download concluído!"))

                    # Obter o arquivo baixado
                    downloaded_file = d['filename']
                    filename = os.path.basename(downloaded_file)

                    # Normalizar o nome do arquivo baixado se necessário
                    normalized_filename = filename

                    if normalized_filename != filename:
                        old_path = downloaded_file
                        new_path = os.path.join(os.path.dirname(old_path), normalized_filename)
                        try:
                            os.rename(old_path, new_path)
                            downloaded_file = new_path
                            self.output_queue.put(("log", f"📝 Arquivo renomeado: {filename} → {normalized_filename}\n"))
                        except Exception as e:
                            self.output_queue.put(("log", f"⚠️ Erro ao renomear arquivo: {e}\n"))

                    self.output_queue.put(("log", f"✅ Download concluído: {os.path.basename(downloaded_file)}\n"))

                    # Definir o arquivo baixado como vídeo atual
                    self.video_path.set(downloaded_file)
                    self.output_queue.put(("log", f"📁 Arquivo definido como vídeo atual: {downloaded_file}\n"))

            # Configurações do yt-dlp para melhor qualidade
            ydl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4',
                'outtmpl': os.path.join(self.downloads_dir.get(), '%(title)s.%(ext)s'),
                'progress_hooks': [progress_hook],
                'noplaylist': True,  # Baixar apenas o vídeo, não a playlist
                'writesubtitles': False,
                'writeautomaticsub': False,
                'merge_output_format': 'mp4',  # Forçar saída mp4
            }

            self.output_queue.put(("status", "🔍 Obtendo informações do vídeo..."))
            self.output_queue.put(("log", f"URL: {url}\n"))
            self.output_queue.put(("log", f"Pasta de download: {self.downloads_dir.get()}\n"))

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Obter informações do vídeo primeiro
                info = ydl.extract_info(url, download=False)
                title = info.get('title', 'Vídeo sem título')
                duration = info.get('duration', 0)
                uploader = info.get('uploader', 'Desconhecido')

                self.output_queue.put(("log", f"📽️ Título: {title}\n"))
                self.output_queue.put(("log", f"📝 Canal: {uploader}\n"))
                self.output_queue.put(("log", f"⏱️ Duração: {duration // 60}:{duration % 60:02d}\n"))

                # Verificar se já existe um arquivo com o mesmo nome
                expected_filename = os.path.join(self.downloads_dir.get(), f"{title}.mp4")
                if os.path.exists(expected_filename):
                    if messagebox.askyesno("Arquivo Existente",
                                         f"O arquivo '{title}.mp4' já existe.\n\nDeseja baixar novamente?"):
                        self.output_queue.put(("log", "🔄 Sobrescrevendo arquivo existente...\n"))
                    else:
                        self.output_queue.put(("log", "📁 Usando arquivo existente...\n"))
                        self.video_path.set(expected_filename)
                        self.output_queue.put(("download_finished", True))
                        return

                # Baixar o vídeo
                self.output_queue.put(("status", f"📥 Baixando: {title}..."))
                ydl.download([url])

                self.output_queue.put(("download_finished", True))

                novo_nome = f"{title}.mp4"
                os.rename('{title}.mp4', '{novo_nome}')
                self.vm_video_path = os.path.basename(novo_nome)

        except Exception as e:
            error_msg = str(e)
            self.output_queue.put(("log", f"❌ Erro no download: {error_msg}\n"))
            self.output_queue.put(("status", "❌ Erro no download"))
            self.output_queue.put(("download_finished", False))

    def browse_video(self):
        filename = filedialog.askopenfilename(
            title="Selecionar Vídeo",
            filetypes=[
                ("Vídeos", "*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.webm"),
                ("Todos os arquivos", "*.*")
            ]
        )
        if filename:
            self.video_path.set(filename)
            # Limpar URL do YouTube se um arquivo local foi selecionado
            self.youtube_url.set("")

    def browse_vm_video(self):
        vm_video_path = filedialog.askopenfilename(
            title="Selecionar Vídeo",
            filetypes=[
                ("Vídeos", "*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.webm"),
                ("Todos os arquivos", "*.*")
            ]
        )
        if vm_video_path:
            self.vm_video_path.set(vm_video_path)
            # Limpar URL do YouTube se um arquivo local foi selecionado
            self.youtube_url.set("")

    def browse_output(self):
        dirname = filedialog.askdirectory(title="Selecionar Pasta de Saída")
        if dirname:
            self.output_dir.set(dirname)

    def browse_temp(self):
        dirname = filedialog.askdirectory(title="Selecionar Pasta Temporária")
        if dirname:
            self.temp_dir.set(dirname)

    def browse_bulk_folder(self):
        dirname = filedialog.askdirectory(title="Selecionar Pasta de Destino")
        if dirname:
            self.bulk_download_dir.set(dirname)

    def clear_bulk_urls(self):
        """Limpar a lista de URLs"""
        self.bulk_urls_text.delete("1.0", "end")

    def validate_bulk_urls(self):
        """Validar todas as URLs na lista"""
        urls = self.bulk_urls_text.get("1.0", "end").strip().split("\n")
        valid_urls = []
        invalid_urls = []

        for url in urls:
            if self.is_valid_youtube_url(url):
                valid_urls.append(url)
            else:
                invalid_urls.append(url)

        # Atualizar lista com URLs válidas
        self.clear_bulk_urls()
        if valid_urls:
            self.bulk_urls_text.insert("end", "\n".join(valid_urls) + "\n")

        # Mostrar mensagem com URLs inválidas, se houver
        if invalid_urls:
            messagebox.showwarning("URLs Inválidas", "As seguintes URLs são inválidas e foram removidas:\n" + "\n".join(invalid_urls))

    def validate_inputs(self):
        if not self.video_path.get():
            messagebox.showerror("Erro", "Por favor, selecione um arquivo de vídeo!")
            return False

        if not os.path.exists(self.video_path.get()):
            messagebox.showerror("Erro", "O arquivo de vídeo não existe!")
            return False

        if not self.output_dir.get():
            messagebox.showerror("Erro", "Por favor, especifique uma pasta de saída!")
            return False

        if self.min_clips.get() < 1:
            messagebox.showerror("Erro", "O número mínimo de clipes deve ser pelo menos 1!")
            return False

        if self.max_clips.get() < self.min_clips.get():
            messagebox.showerror("Erro", "O número máximo de clipes deve ser maior que o mínimo!")
            return False

        if not self.api_key.get():
            messagebox.showwarning("Aviso", "Nenhuma chave API fornecida. O sistema usará métodos alternativos.")

        if not os.path.exists(self.temp_dir.get()):
            messagebox.showerror("Erro", "A pasta temporária não existe!")
            return False

        return True

    def start_processing(self):
        if not self.validate_inputs():
            return

        if self.is_processing:
            messagebox.showwarning("Aviso", "Já existe um processamento em andamento!")
            return

        # Salvar a chave API se fornecida
        if self.api_key.get():
            self.save_config()

        self.is_processing = True
        self.process_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.status_label.configure(text="Iniciando processamento...")
        self.progress_bar['value'] = 0
        self.log_text.delete("1.0", "end")

        # Mudar para a aba de processamento
        self.notebook.select(3)

        # Iniciar thread de processamento
        thread = threading.Thread(target=self.process_video, daemon=True)
        thread.start()

    def stop_processing(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.output_queue.put(("status", "Processamento interrompido pelo usuário"))
            self.output_queue.put(("finished", False))

    def get_video_duration(self, video_path):
        """Obter duração do vídeo em segundos usando ffprobe"""
        try:
            cmd = [
                "ffprobe", "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "csv=p=0",
                video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                duration_seconds = float(result.stdout.strip())
                return duration_seconds
            return 0
        except Exception as e:
            print(f"Erro ao obter duração do vídeo: {e}")
            return 0

    def split_video_into_segments(self, video_path, segment_duration_minutes, temp_dir):
        """Dividir vídeo em segmentos de duração específica"""
        segments = []
        try:
            # Converter duração para segundos
            segment_duration_seconds = segment_duration_minutes * 60

            # Obter duração total do vídeo
            total_duration = self.get_video_duration(video_path)   # Em segundos

            if total_duration <= segment_duration_seconds:
                # Vídeo não precisa ser dividido
                return [video_path]

            self.output_queue.put(("status",
                                   f"🔄 Vídeo tem {total_duration / 60:.1f} min. Dividindo em segmentos de {segment_duration_minutes} min..."))

            # Criar segmentos
            segment_count = 0
            start_time = 0

            while start_time < total_duration:
                segment_count += 1
                end_time = min(start_time + segment_duration_seconds, total_duration)

                # Nome do arquivo do segmento
                video_name = os.path.splitext(os.path.basename(video_path))[0]
                segment_filename = f"{video_name}_segment_{segment_count:03d}.mp4"
                segment_path = os.path.join(temp_dir, segment_filename)

                # Comando ffmpeg para criar o segmento
                cmd = [
                    "ffmpeg", "-i", video_path,
                    "-ss", str(start_time),
                    "-t", str(end_time - start_time),
                    "-c", "copy",  # Cópia sem recodificação para ser mais rápido
                    "-avoid_negative_ts", "make_zero",
                    "-y",  # Sobrescrever se existir
                    segment_path
                ]

                self.output_queue.put(("log", f"Criando segmento {segment_count}: {segment_filename}\n"))
                self.output_queue.put(("status",
                                       f"🔄 Criando segmento {segment_count}/{int((total_duration / segment_duration_seconds) + 1)}..."))

                # Executar comando ffmpeg
                result = subprocess.run(cmd, capture_output=True, text=True)

                if result.returncode == 0:
                    segments.append(segment_path)
                    self.output_queue.put(("log", f"✅ Segmento {segment_count} criado com sucesso\n"))
                else:
                    self.output_queue.put(("log", f"❌ Erro ao criar segmento {segment_count}: {result.stderr}\n"))
                    break

                start_time = end_time

            self.output_queue.put(("status", f"✅ Vídeo dividido em {len(segments)} segmentos"))
            return segments

        except Exception as e:
            self.output_queue.put(("error", f"Erro ao dividir vídeo: {str(e)}"))
            return [video_path]  # Retornar vídeo original em caso de erro

    def process_video(self):
        try:
            # Criar pasta de saída se não existir
            os.makedirs(self.output_dir.get(), exist_ok=True)

            # Criar pasta temporária se não existir
            os.makedirs(self.temp_dir.get(), exist_ok=True)

            # Dividir vídeo em segmentos se a duração máxima for maior que 0
            segments = []
            if self.max_segment_duration.get() > 0:
                self.output_queue.put(("status", "🔄 Dividindo vídeo em segmentos..."))
                segments = self.split_video_into_segments(self.video_path.get(), self.max_segment_duration.get(),
                                                          self.temp_dir.get())
                if not segments or len(segments) == 0:
                    self.output_queue.put(("status", "❌ Erro ao dividir vídeo em segmentos"))
                    return
            else:
                segments = [self.video_path.get()]

            # Processar cada segmento individualmente
            for i, segment_path in enumerate(segments):
                self.output_queue.put(("status", f"🎬 Processando segmento {i + 1}/{len(segments)}..."))

                # Construir comando
                cmd = [
                    "python", "generateClips.py",
                    segment_path,
                    "--output-dir", self.output_dir.get(),
                    "--min-clips", str(self.min_clips.get()),
                    "--max-clips", str(self.max_clips.get()),
                    "--whisper-model", self.whisper_model.get(),
                    "--mode", self.mode.get()
                ]

                if self.api_key.get():
                    cmd.extend(["--api-key", self.api_key.get()])

                if self.no_review.get():
                    cmd.append("--no-review")

                self.output_queue.put(("log", f"Comando: {' '.join(cmd)}\n"))

                # Executar comando
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )

                # Ler saída em tempo real
                progress_value = 0
                while True:
                    output = self.process.stdout.readline()
                    if output == '' and self.process.poll() is not None:
                        break
                    if output:
                        self.output_queue.put(("log", output))

                        # Atualizar progresso baseado na saída com mais detalhes
                        if "Splitting video into segments" in output or "Splitting large video" in output:
                            progress_value = 5
                            self.output_queue.put(("progress", progress_value))
                            self.output_queue.put(("status", "🔄 Dividindo vídeo em segmentos..."))
                        elif "Extracting audio" in output or "audio extraction" in output:
                            progress_value = 15
                            self.output_queue.put(("progress", progress_value))
                            self.output_queue.put(("status", "🎵 Extraindo áudio..."))
                        elif "Transcribing" in output or "transcription" in output:
                            progress_value = min(progress_value + 5, 70)  # Incrementar gradualmente
                            self.output_queue.put(("progress", progress_value))
                            # Extrair informações mais específicas da transcrição
                            if "segment" in output.lower():
                                segment_info = output.strip()
                                self.output_queue.put(("status", f"🎤 Transcrevendo: {segment_info}"))
                            else:
                                self.output_queue.put(("status", "🎤 Transcrevendo áudio..."))
                        elif "Processing transcription" in output:
                            progress_value = 75
                            self.output_queue.put(("progress", progress_value))
                            self.output_queue.put(("status", "📝 Processando transcrições..."))
                        elif "Finding interesting moments" in output or "analyzing" in output:
                            progress_value = 80
                            self.output_queue.put(("progress", progress_value))
                            self.output_queue.put(("status", "🔍 Analisando momentos interessantes..."))
                        elif "Creating clip" in output:
                            progress_value = min(progress_value + 3, 95)
                            self.output_queue.put(("progress", progress_value))
                            self.output_queue.put(("status", "🎬 Criando clipes..."))
                        elif "Successfully created clip" in output:
                            # Extrair nome do clipe se possível
                            if ":" in output:
                                clip_name = output.split(":")[-1].strip()
                                self.output_queue.put(("status", f"✅ Clipe criado: {clip_name}"))
                        elif "Process complete" in output or "completed successfully" in output:
                            progress_value = 100
                            self.output_queue.put(("progress", progress_value))
                            self.output_queue.put(("status", "🎉 Processamento concluído!"))
                        elif "Error" in output or "error" in output.lower():
                            self.output_queue.put(("status", "❌ Erro detectado - verifique o log"))
                        elif "%" in output and any(
                                word in output.lower() for word in ["progress", "processing", "complete"]):
                            # Tentar extrair porcentagem do output
                            try:
                                # Usar regex para extrair números antes do %
                                percentage_match = re.search(r'(\d+)%', output)
                                if percentage_match:
                                    percentage = int(percentage_match.group(1))
                                    progress_value = min(percentage, 95)
                                    self.output_queue.put(("progress", progress_value))
                            except:
                                pass

            # Verificar código de saída
            return_code = self.process.poll()
            if return_code == 0:
                self.output_queue.put(("finished", True))
            else:
                self.output_queue.put(("finished", False))

        except Exception as e:
            self.output_queue.put(("error", str(e)))
            self.output_queue.put(("finished", False))

    def start_bulk_download(self):
        """Iniciar download em massa de vídeos"""
        urls_text = self.bulk_urls_text.get("1.0", "end").strip()

        if not urls_text:
            messagebox.showerror("Erro", "Por favor, adicione URLs para download!")
            return

        urls = [url.strip() for url in urls_text.split("\n") if url.strip()]

        if not urls:
            messagebox.showerror("Erro", "Nenhuma URL válida encontrada!")
            return

        if self.is_downloading:
            messagebox.showwarning("Aviso", "Já existe um download em andamento!")
            return

        # Criar pasta de download em massa se não existir
        os.makedirs(self.bulk_download_dir.get(), exist_ok=True)

        # Iniciar download em thread separada
        self.is_downloading = True
        self.bulk_download_button.configure(state="disabled")
        self.notebook.select(3)  # Mudar para aba de processamento
        self.status_label.configure(text="🔄 Iniciando download em massa...")
        self.progress_bar['value'] = 0
        self.log_text.delete("1.0", "end")

        thread = threading.Thread(target=self.bulk_download_thread, args=(urls,), daemon=True)
        thread.start()

    def bulk_download_thread(self, urls):
        """Thread para download em massa de vídeos"""
        try:
            total_urls = len(urls)
            downloaded = 0
            failed = 0

            self.output_queue.put(("log", f"📥 Iniciando download de {total_urls} vídeos...\n"))
            self.output_queue.put(("log", f"📁 Pasta de destino: {self.bulk_download_dir.get()}\n\n"))

            for i, url in enumerate(urls, 1):
                if not self.is_valid_youtube_url(url):
                    self.output_queue.put(("log", f"❌ URL inválida: {url}\n"))
                    failed += 1
                    continue

                self.output_queue.put(("status", f"📥 Baixando {i}/{total_urls}: {url[:50]}..."))
                self.output_queue.put(("log", f"🔄 Processando {i}/{total_urls}: {url}\n"))

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
                                self.output_queue.put(("progress", min(global_progress, 95)))

                                # Atualizar status com informações de download
                                speed = d.get('speed', 0)
                                if speed:
                                    speed_mb = speed / 1024 / 1024
                                    self.output_queue.put(("status", f"📥 Baixando {i}/{total_urls} - {speed_mb:.1f} MB/s"))

                            except Exception as e:
                                self.output_queue.put(("log", f"Erro ao processar progresso: {e}\n"))

                        elif d['status'] == 'finished':
                            filename = os.path.basename(d['filename'])
                            # Normalizar o nome do arquivo
                            normalized_filename = filename
                            if normalized_filename != filename:
                                old_path = d['filename']
                                new_path = os.path.join(os.path.dirname(old_path), normalized_filename)
                                try:
                                    os.rename(old_path, new_path)
                                    self.output_queue.put(("log", f"📝 Arquivo renomeado: {filename} → {normalized_filename}\n"))
                                except Exception as e:
                                    self.output_queue.put(("log", f"⚠️ Erro ao renomear arquivo: {e}\n"))

                            self.output_queue.put(("log", f"✅ Download concluído: {normalized_filename}\n"))

                    # Configurações do yt-dlp
                    ydl_opts = {
                        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4',
                        'outtmpl': os.path.join(self.bulk_download_dir.get(), '%(title)s.%(ext)s'),
                        'progress_hooks': [progress_hook],
                        'noplaylist': True,
                        'writesubtitles': False,
                        'writeautomaticsub': False,
                        'writethumbnail': self.download_thumbnails.get(),
                    }

                    # Configurar formato das thumbnails se habilitado
                    if self.download_thumbnails.get():
                        ydl_opts['postprocessors'] = ydl_opts.get('postprocessors', [])
                        ydl_opts['postprocessors'].append({
                            'key': 'FFmpegThumbnailsConvertor',
                            'format': self.thumbnail_format.get(),
                        })

                    if self.audio_only.get():
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

                        self.output_queue.put(("log", f"📽️ Título: {title}\n"))
                        self.output_queue.put(("log", f"📝 Canal: {uploader}\n"))
                        self.output_queue.put(("log", f"⏱️ Duração: {duration // 60}:{duration % 60:02d}\n"))

                        # Verificar se já existe
                        normalized_title = title
                        ext = 'mp3' if self.audio_only.get() else 'mp4'
                        expected_filename = os.path.join(self.bulk_download_dir.get(), f"{normalized_title}.{ext}")

                        if os.path.exists(expected_filename):
                            self.output_queue.put(("log", f"📁 Arquivo já existe, pulando: {normalized_title}.{ext}\n"))
                            downloaded += 1
                        else:
                            # Baixar o vídeo
                            ydl.download([url])
                            downloaded += 1

                        self.output_queue.put(("log", f"✅ Processado {i}/{total_urls}\n\n"))

                except Exception as e:
                    self.output_queue.put(("log", f"❌ Erro ao baixar {url}: {str(e)}\n\n"))
                    failed += 1

                # Atualizar progresso global
                global_progress = (i / total_urls) * 100
                self.output_queue.put(("progress", global_progress))

            # Finalizar
            self.output_queue.put(("progress", 100))
            self.output_queue.put(("status", f"✅ Download em massa concluído!"))
            self.output_queue.put(("log", f"\n🎉 Download em massa finalizado!\n"))
            self.output_queue.put(("log", f"✅ Sucessos: {downloaded}\n"))
            self.output_queue.put(("log", f"❌ Falhas: {failed}\n"))
            self.output_queue.put(("log", f"📁 Pasta: {self.bulk_download_dir.get()}\n"))

            self.output_queue.put(("bulk_download_finished", True))

        except Exception as e:
            error_msg = str(e)
            self.output_queue.put(("log", f"❌ Erro no download em massa: {error_msg}\n"))
            self.output_queue.put(("status", "❌ Erro no download em massa"))
            self.output_queue.put(("bulk_download_finished", False))

    def check_queue(self):
        try:
            while True:
                msg_type, data = self.output_queue.get_nowait()

                if msg_type == "status":
                    self.status_label.configure(text=data)
                elif msg_type == "progress":
                    self.progress_bar['value'] = data
                elif msg_type == "log":
                    self.log_text.insert("end", data)
                    self.log_text.see("end")
                elif msg_type == "error":
                    messagebox.showerror("Erro", f"Erro durante o processamento:\n{data}")
                elif msg_type == "download_finished":
                    self.is_downloading = False
                    if data:  # Sucesso
                        messagebox.showinfo("Download Concluído",
                                          f"Download do YouTube concluído com sucesso!\n\nO vídeo foi salvo em:\n{self.downloads_dir.get()}")
                        # Voltar para a aba básica
                        self.notebook.select(0)
                    else:  # Falha
                        messagebox.showerror("Erro", "O download falhou. Verifique o log para mais detalhes.")
                elif msg_type == "bulk_download_finished":
                    self.is_downloading = False
                    self.bulk_download_button.configure(state="normal")
                    if data:  # Sucesso
                        messagebox.showinfo("Download em Massa Concluído",
                                          f"Download em massa concluído!\n\nOs arquivos foram salvos em:\n{self.bulk_download_dir.get()}")
                        # Abrir pasta de download em massa
                        if messagebox.askyesno("Abrir Pasta", "Deseja abrir a pasta de download em massa?"):
                            try:
                                subprocess.run(["xdg-open", self.bulk_download_dir.get()])
                            except Exception as e:
                                print(f"Erro ao abrir pasta: {e}")
                        # Voltar para a aba de download em massa
                        self.notebook.select(1)
                    else:  # Falha
                        messagebox.showerror("Erro", "O download em massa falhou. Verifique o log para mais detalhes.")
                elif msg_type == "finished":
                    self.is_processing = False
                    self.process_button.configure(state="normal")
                    self.stop_button.configure(state="disabled")

                    if data:  # Sucesso
                        messagebox.showinfo("Sucesso",
                                            f"Processamento concluído com sucesso!\n\nOs clipes foram salvos em:\n{self.output_dir.get()}")
                        # Abrir pasta de saída
                        if messagebox.askyesno("Abrir Pasta", "Deseja abrir a pasta de saída?"):
                            self.open_output_folder()
                    else:  # Falha
                        messagebox.showerror("Erro", "O processamento falhou. Verifique o log para mais detalhes.")
                elif msg_type == "vm_finished":
                    self.vm_is_processing = False
                    self.gerar_video_button.configure(state="normal")
                    success, output_file = data

                    if success:  # Sucesso
                        messagebox.showinfo("Vídeo Processado",
                                          f"Vídeo processado com sucesso!\n\nO arquivo foi salvo em:\n{output_file}")
                        # Abrir pasta de saída
                        if messagebox.askyesno("Abrir Pasta", "Deseja abrir a pasta onde o vídeo foi salvo?"):
                            try:
                                folder_path = os.path.dirname(output_file)
                                subprocess.run(["xdg-open", folder_path])
                            except Exception as e:
                                print(f"Erro ao abrir pasta: {e}")
                        # Voltar para a aba Vídeo Maker
                        self.notebook.select(4)
                    else:  # Falha
                        messagebox.showerror("Erro", "O processamento do vídeo falhou. Verifique o log para mais detalhes.")

        except queue.Empty:
            pass

        # Agendar próxima verificação
        self.root.after(100, self.check_queue)

    def gerar_video(self):
        """Gerar vídeo usando o caminho separado do Video Maker"""
        if not self.vm_video_path.get():
            messagebox.showerror("Erro", "Por favor, selecione um arquivo de vídeo no Video Maker!")
            return

        video_path = self.vm_video_path.get()

        if not os.path.exists(video_path):
            messagebox.showerror("Erro", "O arquivo de vídeo não existe!")
            return

        duration = self.get_video_duration(video_path)
        if duration is None:
            return

        use_sponsor = self.vm_sponsor_block.get()
        use_bars = self.vm_black_bars.get()
        try:
            bars_height = int(self.vm_black_bars_height.get()) if use_bars else 0
        except:
            messagebox.showerror("Erro", "Altura das barras inválida.")
            return

        use_cut = self.vm_cut_last_seconds.get()
        try:
            cut_seconds = int(self.vm_cut_seconds.get()) if use_cut else 0
        except:
            messagebox.showerror("Erro", "Valor inválido para corte de segundos.")
            return

        render_opt = self.vm_quality.get()
        render_map = {
            "720p 30fps": ("1280:720", 30),
            "1080p 30fps": ("1920:1080", 30),
            "480p 30fps": ("854:480", 30),
        }
        scale_res, fps = render_map.get(render_opt, ("1920:1080", 30))

        sponsor_segments = []
        if use_sponsor and self.vm_video_id:
            sponsor_segments = self.get_sponsor_segments(self.vm_video_id)
        elif use_sponsor and not self.vm_video_id:
            if not messagebox.askyesno("Aviso",
                                       "ID do YouTube não encontrado no arquivo/link.\nNão será possível usar SponsorBlock.\nContinuar sem SponsorBlock?"):
                return

        # Criar pasta /prontos se não existir
        prontos_dir = "prontos"
        os.makedirs(prontos_dir, exist_ok=True)

        # Salvar o arquivo processado na pasta /prontos
        base_filename = os.path.splitext(os.path.basename(video_path))[0]
        output_file = os.path.join(prontos_dir, f"{base_filename}_processado.mp4")

        # Iniciar processamento em thread separada
        self.vm_is_processing = True
        self.gerar_video_button.configure(state="disabled")
        self.notebook.select(3)  # Mudar para aba de processamento
        self.status_label.configure(text="🎬 Processando vídeo...")
        self.progress_bar['value'] = 0
        self.log_text.delete("1.0", "end")

        thread = threading.Thread(target=self.process_video_maker,
                                args=(video_path, output_file, sponsor_segments, bars_height, cut_seconds, scale_res, fps),
                                daemon=True)
        thread.start()

    def process_video_maker(self, video_path, output_file, sponsor_segments, bars_height, cut_seconds, scale_res, fps):
        """Processar vídeo no Video Maker"""
        try:
            # Construir filtro complexo
            duration = self.get_video_duration(video_path)  # retorna segundos
            print(duration)
            print(video_path)
            filter_complex = self.build_filter_complex(
                duration,  # ✅ Agora é número
                sponsor_segments,
                bars_height,
                cut_seconds,
                scale_res
            )

            if filter_complex is None:
                self.output_queue.put(("vm_finished", (False, "")))
                return

            cmd = [
                "ffmpeg", "-y", "-i", video_path,
                "-filter_complex", filter_complex,
                "-map", "[vfinal]", "-map", "[aout]",
                "-r", str(fps),
                "-c:v", "libx264",
                "-preset", "slow",
                "-crf", "18",
                "-c:a", "aac",
                "-b:a", "192k",
                output_file
            ]

            self.output_queue.put(("log", f"Executando FFmpeg: {' '.join(cmd)}\n"))
            self.output_queue.put(("status", "🎬 Processando vídeo com FFmpeg..."))

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
            progress_value = 0
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    self.output_queue.put(("log", output))

                    # Atualizar progresso
                    if "frame=" in output:
                        progress_value = min(progress_value + 1, 95)
                        self.output_queue.put(("progress", progress_value))

            # Verificar resultado
            return_code = process.poll()
            if return_code == 0:
                self.output_queue.put(("progress", 100))
                self.output_queue.put(("status", "✅ Vídeo processado com sucesso!"))
                self.output_queue.put(("vm_finished", (True, output_file)))
            else:
                self.output_queue.put(("vm_finished", (False, "")))

        except Exception as e:
            self.output_queue.put(("log", f"❌ Erro ao processar vídeo: {str(e)}\n"))
            self.output_queue.put(("vm_finished", (False, "")))

    def build_filter_complex(self, duration, sponsor_segments, bars_height, cut_last_seconds, scale_res):
        final_duration = float(duration) - int(cut_last_seconds)
        if final_duration <= 0:
            messagebox.showerror("Erro", "O corte dos últimos segundos excede a duração do vídeo.")
            return None

        intervals = []
        start = 0.0
        sorted_segs = sorted(sponsor_segments, key=lambda x: x[0])

        for seg in sorted_segs:
            seg_start, seg_end = seg
            if seg_start >= final_duration:
                break
            if seg_start > start:
                intervals.append((start, min(seg_start, final_duration)))
            start = max(start, seg_end)
        if start < final_duration:
            intervals.append((start, final_duration))

        if not intervals:
            intervals = [(0, final_duration)]

        filter_parts = []
        for i, (s, e) in enumerate(intervals):
            filter_parts.append(f"[0:v]trim=start={s}:end={e},setpts=PTS-STARTPTS[v{i}];")
            filter_parts.append(f"[0:a]atrim=start={s}:end={e},asetpts=PTS-STARTPTS[a{i}];")

        v_streams = "".join([f"[v{i}]" for i in range(len(intervals))])
        a_streams = "".join([f"[a{i}]" for i in range(len(intervals))])

        filter_parts.append(f"{v_streams}concat=n={len(intervals)}:v=1:a=0[vout];")
        filter_parts.append(f"{a_streams}concat=n={len(intervals)}:v=0:a=1[aout];")

        if bars_height > 0:
            # Primeiro escala para a resolução desejada, depois corta as partes de cima e baixo
            # e adiciona barras pretas para manter o aspect ratio
            width, height = map(int, scale_res.split(':'))
            crop_height = height - (bars_height * 2)
            y_offset = bars_height

            filter_parts.append(f"[vout]scale={scale_res},crop={width}:{crop_height}:0:{y_offset},pad={width}:{height}:0:{bars_height}:black[vfinal]")
        else:
            # Se não usar barras, só escala para a resolução desejada
            filter_parts.append(f"[vout]scale={scale_res}[vfinal]")

        filter_complex = "".join(filter_parts)

        return filter_complex

    def get_sponsor_segments(self, video_id):
        client = sb.Client()
        try:
            segments = client.get_skip_segments(video_id)
            sponsors = [seg for seg in segments if seg.category == "sponsor"]
            return [(seg.start, seg.end) for seg in sponsors]
        except Exception as e:
            messagebox.showwarning("Aviso", f"Erro na SponsorBlock API~: {e}. Ignorando cortes.")
            return []

    def gerar_prompt_thumbnail(self):
        personagens = self.vm_personagens.get().strip()
        texto_thumb = self.vm_texto_thumb.get().strip()
        titulo = self.vm_video_title if self.vm_video_title else "TITULO"

        prompt = f"""Gere uma thumbnail no formato 16:9 com qualidade fotográfica e estilo de thumbnail política para YouTube.

Contexto do vídeo: "{titulo}"
Personagens na imagem: {personagens if personagens else "XXXX,XXXX"}
Texto em tela (grande, chamativo, cores vibrantes, tipografia semelhante às usadas em thumbnails jornalísticas): "{texto_thumb if texto_thumb else "ESCRITA NA THUMB"}"

Elementos visuais:

Fundo contextual que combine com o título do vídeo

Personagens com expressões faciais fortes e condizentes com o contexto (raiva, surpresa, medo, seriedade, riso irônico, etc.).

Iluminação dramática e contraste alto para destacar os elementos principais.

Texto posicionado de forma clara e legível, mantendo o estilo de cores vibrantes e contorno forte.

Paleta de cores rica, com predominância de amarelo, verde, azul e vermelho (quando apropriado ao tema político).

OBS Importante: Não coloque texto e nem rostos, ou algo relevante no 1/4 inferior esquerdo da imagem. Pois eu, manualmente colocarei o rosto do apresentador. Apenas deixe com fundo essa parte ou com trechos não relevantes da imagem.

Não incluir logos de canais.
Usar composição que atraia cliques e gere curiosidade."""

        self.text_prompt.delete("1.0", tk.END)
        self.text_prompt.insert(tk.END, prompt)

    def copiar_prompt(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.text_prompt.get("1.0", tk.END).strip())
        messagebox.showinfo("Prompt copiado", "O prompt foi copiado para a área de transferência.")

    def open_output_folder(self):
        try:
            subprocess.run(["xdg-open", self.output_dir.get()])
        except Exception as e:
            print(f"Erro ao abrir pasta: {e}")

    def run(self):
        self.root.mainloop()


def main():
    app = ClipGeneratorGUI()
    app.run()


if __name__ == "__main__":
    main()
