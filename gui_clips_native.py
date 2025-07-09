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

class ClipGeneratorGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🎬 Gerador de Clipes com IA")
        self.root.geometry("1280x900")
        self.root.resizable(True, True)

        # Configurar tema escuro
        self.root.configure(bg='#2b2b2b')

        # Configurar estilo do ttk
        self.style = ttk.Style()
        self.style.theme_use('clam')

        # Cores personalizadas
        self.bg_color = '#2b2b2b'
        self.fg_color = '#ffffff'
        self.accent_color = '#0078d4'
        self.frame_color = '#3c3c3c'
        self.entry_color = '#404040'

        # Configurar estilos personalizados
        self.setup_styles()

        # Arquivo de configuração
        self.config_file = os.path.join(os.path.dirname(__file__), 'user_config.json')
        
        # Carregar configurações salvas
        self.load_config()

        # Variáveis
        self.video_path = tk.StringVar()
        self.output_dir = tk.StringVar(value="output_folder")
        self.min_clips = tk.IntVar(value=3)
        self.max_clips = tk.IntVar(value=8)
        self.whisper_model = tk.StringVar(value="base")
        self.api_key = tk.StringVar(value=self.saved_api_key)  # Carregar chave salva
        self.captions = tk.BooleanVar(value=True)
        self.no_review = tk.BooleanVar(value=True)
        self.max_segment_duration = tk.IntVar(value=30)  # Nova variável para duração máxima
        self.temp_dir = tk.StringVar(value=os.path.join(tempfile.gettempdir(), "video_segments"))

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

    def setup_styles(self):
        # Configurar estilos ttk
        self.style.configure('Custom.TFrame', background=self.frame_color)
        self.style.configure('Custom.TLabel', background=self.frame_color, foreground=self.fg_color, font=('Arial', 10))
        self.style.configure('Title.TLabel', background=self.bg_color, foreground=self.fg_color, font=('Arial', 20, 'bold'))
        self.style.configure('Subtitle.TLabel', background=self.bg_color, foreground='#cccccc', font=('Arial', 12))
        self.style.configure('Bold.TLabel', background=self.frame_color, foreground=self.fg_color, font=('Arial', 10, 'bold'))
        self.style.configure('Custom.TEntry', insertcolor=self.fg_color, fieldbackground=self.entry_color, foreground=self.fg_color)
        self.style.configure('Custom.TButton', background=self.accent_color, foreground=self.fg_color, font=('Arial', 10, 'bold'))
        self.style.configure('Success.TButton', background='#28a745', foreground=self.fg_color, font=('Arial', 12, 'bold'))
        self.style.configure('Danger.TButton', background='#dc3545', foreground=self.fg_color, font=('Arial', 12, 'bold'))
        self.style.configure('Custom.TCombobox', fieldbackground=self.entry_color, foreground=self.fg_color)
        self.style.configure('Custom.TCheckbutton', background=self.frame_color, foreground=self.fg_color, font=('Arial', 10))

        # Configurar mapa de estados
        self.style.map('Custom.TButton', background=[('active', '#106ebe'), ('pressed', '#005a9e')])
        self.style.map('Success.TButton', background=[('active', '#218838'), ('pressed', '#1e7e34')])
        self.style.map('Danger.TButton', background=[('active', '#c82333'), ('pressed', '#bd2130')])

    def setup_ui(self):
        # Frame principal
        main_frame = ttk.Frame(self.root, style='Custom.TFrame')
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Título
        title_label = ttk.Label(
            main_frame,
            text="🎬 Gerador de Clipes com IA",
            style='Title.TLabel'
        )
        title_label.pack(pady=(10, 5))

        # Subtitle
        subtitle_label = ttk.Label(
            main_frame,
            text="Transforme seus vídeos em clipes curtos automaticamente",
            style='Subtitle.TLabel'
        )
        subtitle_label.pack(pady=(0, 20))

        # Notebook para organizar as configurações
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Tab 1: Configurações básicas
        self.setup_basic_tab()

        # Tab 2: Configurações avançadas
        self.setup_advanced_tab()

        # Tab 3: Processamento
        self.setup_processing_tab()

        # Frame de botões
        button_frame = ttk.Frame(main_frame, style='Custom.TFrame')
        button_frame.pack(fill="x", padx=10, pady=10)

        # Botão processar
        self.process_button = ttk.Button(
            button_frame,
            text="🚀 Processar Vídeo",
            command=self.start_processing,
            style='Success.TButton'
        )
        self.process_button.pack(side="left", padx=5, pady=5, ipadx=20, ipady=10)

        # Botão parar
        self.stop_button = ttk.Button(
            button_frame,
            text="⏹️ Parar",
            command=self.stop_processing,
            state="disabled",
            style='Danger.TButton'
        )
        self.stop_button.pack(side="right", padx=5, pady=5, ipadx=20, ipady=10)

    def setup_basic_tab(self):
        # Frame da aba básica
        basic_frame = ttk.Frame(self.notebook, style='Custom.TFrame')
        self.notebook.add(basic_frame, text="📁 Básico")

        # Canvas e scrollbar para rolagem
        canvas = tk.Canvas(basic_frame, bg=self.frame_color, highlightthickness=0)
        scrollbar = ttk.Scrollbar(basic_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style='Custom.TFrame')

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Seleção de vídeo
        video_frame = ttk.LabelFrame(scrollable_frame, text="📹 Arquivo de Vídeo", style='Custom.TFrame')
        video_frame.pack(fill="x", padx=20, pady=10)

        video_input_frame = ttk.Frame(video_frame, style='Custom.TFrame')
        video_input_frame.pack(fill="x", padx=10, pady=10)

        self.video_entry = ttk.Entry(
            video_input_frame,
            textvariable=self.video_path,
            style='Custom.TEntry',
            width=50
        )
        self.video_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        ttk.Button(
            video_input_frame,
            text="📂 Navegar",
            command=self.browse_video,
            style='Custom.TButton'
        ).pack(side="right", padx=(5, 0), ipadx=10)

        # Pasta de saída
        output_frame = ttk.LabelFrame(scrollable_frame, text="📁 Pasta de Saída", style='Custom.TFrame')
        output_frame.pack(fill="x", padx=20, pady=10)

        output_input_frame = ttk.Frame(output_frame, style='Custom.TFrame')
        output_input_frame.pack(fill="x", padx=10, pady=10)

        self.output_entry = ttk.Entry(
            output_input_frame,
            textvariable=self.output_dir,
            style='Custom.TEntry',
            width=50
        )
        self.output_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        ttk.Button(
            output_input_frame,
            text="📂 Navegar",
            command=self.browse_output,
            style='Custom.TButton'
        ).pack(side="right", padx=(5, 0), ipadx=10)

        # Número de clipes
        clips_frame = ttk.LabelFrame(scrollable_frame, text="🎯 Quantidade de Clipes", style='Custom.TFrame')
        clips_frame.pack(fill="x", padx=20, pady=10)

        clips_config_frame = ttk.Frame(clips_frame, style='Custom.TFrame')
        clips_config_frame.pack(fill="x", padx=10, pady=10)

        # Min clips
        ttk.Label(clips_config_frame, text="Mínimo:", style='Custom.TLabel').pack(side="left", padx=(0, 5))
        min_spinbox = tk.Spinbox(clips_config_frame, from_=1, to=50, textvariable=self.min_clips,
                                width=10, bg=self.entry_color, fg=self.fg_color, insertbackground=self.fg_color)
        min_spinbox.pack(side="left", padx=(0, 20))

        # Max clips
        ttk.Label(clips_config_frame, text="Máximo:", style='Custom.TLabel').pack(side="left", padx=(0, 5))
        max_spinbox = tk.Spinbox(clips_config_frame, from_=1, to=100, textvariable=self.max_clips,
                                width=10, bg=self.entry_color, fg=self.fg_color, insertbackground=self.fg_color)
        max_spinbox.pack(side="left")

    def setup_advanced_tab(self):
        # Frame da aba avançada
        advanced_frame = ttk.Frame(self.notebook, style='Custom.TFrame')
        self.notebook.add(advanced_frame, text="⚙️ Avançado")

        # Canvas e scrollbar para rolagem
        canvas = tk.Canvas(advanced_frame, bg=self.frame_color, highlightthickness=0)
        scrollbar = ttk.Scrollbar(advanced_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style='Custom.TFrame')

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Modelo Whisper
        whisper_frame = ttk.LabelFrame(scrollable_frame, text="🎤 Modelo Whisper", style='Custom.TFrame')
        whisper_frame.pack(fill="x", padx=20, pady=10)

        whisper_combo = ttk.Combobox(
            whisper_frame,
            values=["tiny", "base", "small", "medium", "large"],
            textvariable=self.whisper_model,
            style='Custom.TCombobox',
            state="readonly"
        )
        whisper_combo.pack(padx=10, pady=10, fill="x")

        # API Key
        api_frame = ttk.LabelFrame(scrollable_frame, text="🔑 Chave API do Google Gemini", style='Custom.TFrame')
        api_frame.pack(fill="x", padx=20, pady=10)

        self.api_entry = ttk.Entry(
            api_frame,
            textvariable=self.api_key,
            style='Custom.TEntry',
            show="*"
        )
        self.api_entry.pack(fill="x", padx=10, pady=10)

        # Opções
        options_frame = ttk.LabelFrame(scrollable_frame, text="🎛️ Opções", style='Custom.TFrame')
        options_frame.pack(fill="x", padx=20, pady=10)

        # Checkbox para não revisar
        self.no_review_checkbox = ttk.Checkbutton(
            options_frame,
            text="Processar sem revisão manual",
            variable=self.no_review,
            style='Custom.TCheckbutton'
        )
        self.no_review_checkbox.pack(anchor="w", padx=10, pady=(5, 10))

        # Duração máxima do segmento
        duration_frame = ttk.LabelFrame(scrollable_frame, text="⏱️ Duração Máxima do Segmento", style='Custom.TFrame')
        duration_frame.pack(fill="x", padx=20, pady=10)

        ttk.Label(duration_frame, text="Duração máxima de cada segmento em minutos:", style='Custom.TLabel').pack(anchor="w", padx=10, pady=(5, 0))

        duration_spinbox = tk.Spinbox(
            duration_frame,
            from_=1,
            to=300,
            textvariable=self.max_segment_duration,
            width=10,
            bg=self.entry_color,
            fg=self.fg_color,
            insertbackground=self.fg_color
        )
        duration_spinbox.pack(side="left", padx=10, pady=10)

        # Pasta temporária
        temp_frame = ttk.LabelFrame(scrollable_frame, text="📂 Pasta Temporária", style='Custom.TFrame')
        temp_frame.pack(fill="x", padx=20, pady=10)

        ttk.Label(temp_frame, text="Pasta onde os segmentos de vídeo serão armazenados temporariamente:", style='Custom.TLabel').pack(anchor="w", padx=10, pady=(5, 0))

        temp_entry = ttk.Entry(
            temp_frame,
            textvariable=self.temp_dir,
            style='Custom.TEntry',
            width=50
        )
        temp_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        ttk.Button(
            temp_frame,
            text="📂 Navegar",
            command=self.browse_temp,
            style='Custom.TButton'
        ).pack(side="right", padx=(5, 0), ipadx=10)

    def setup_processing_tab(self):
        # Frame da aba de processamento
        processing_frame = ttk.Frame(self.notebook, style='Custom.TFrame')
        self.notebook.add(processing_frame, text="⚡ Processamento")

        # Status
        status_frame = ttk.LabelFrame(processing_frame, text="📊 Status", style='Custom.TFrame')
        status_frame.pack(fill="x", padx=20, pady=10)

        self.status_label = ttk.Label(
            status_frame,
            text="Aguardando...",
            style='Custom.TLabel'
        )
        self.status_label.pack(anchor="w", padx=10, pady=10)

        # Barra de progresso
        progress_frame = ttk.LabelFrame(processing_frame, text="📈 Progresso", style='Custom.TFrame')
        progress_frame.pack(fill="x", padx=20, pady=10)

        self.progress_bar = ttk.Progressbar(
            progress_frame,
            mode='determinate'
        )
        self.progress_bar.pack(fill="x", padx=10, pady=10)

        # Log de saída
        log_frame = ttk.LabelFrame(processing_frame, text="📝 Log de Processamento", style='Custom.TFrame')
        log_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Frame para text widget e scrollbar
        text_frame = ttk.Frame(log_frame, style='Custom.TFrame')
        text_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Text widget para o log
        self.log_text = tk.Text(
            text_frame,
            height=15,
            bg=self.entry_color,
            fg=self.fg_color,
            insertbackground=self.fg_color,
            font=('Consolas', 10)
        )

        # Scrollbar para o text widget
        log_scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)

        self.log_text.pack(side="left", fill="both", expand=True)
        log_scrollbar.pack(side="right", fill="y")

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

    def browse_output(self):
        dirname = filedialog.askdirectory(title="Selecionar Pasta de Saída")
        if dirname:
            self.output_dir.set(dirname)

    def browse_temp(self):
        dirname = filedialog.askdirectory(title="Selecionar Pasta Temporária")
        if dirname:
            self.temp_dir.set(dirname)

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
        self.log_text.delete("1.0", tk.END)

        # Mudar para a aba de processamento
        self.notebook.select(2)  # Selecionar a terceira aba (índice 2)

        # Iniciar thread de processamento
        thread = threading.Thread(target=self.process_video, daemon=True)
        thread.start()

    def stop_processing(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.output_queue.put(("status", "Processamento interrompido pelo usuário"))
            self.output_queue.put(("finished", False))

    def get_video_duration(self, video_path):
        """Obter duração do vídeo em minutos usando ffprobe"""
        try:
            cmd = ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", video_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                duration_seconds = float(result.stdout.strip())
                return duration_seconds / 60  # Converter para minutos
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
            total_duration = self.get_video_duration(video_path) * 60  # Em segundos

            if total_duration <= segment_duration_seconds:
                # Vídeo não precisa ser dividido
                return [video_path]

            self.output_queue.put(("status", f"🔄 Vídeo tem {total_duration/60:.1f} min. Dividindo em segmentos de {segment_duration_minutes} min..."))

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
                self.output_queue.put(("status", f"🔄 Criando segmento {segment_count}/{int((total_duration/segment_duration_seconds) + 1)}..."))

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
                segments = self.split_video_into_segments(self.video_path.get(), self.max_segment_duration.get(), self.temp_dir.get())
                if not segments or len(segments) == 0:
                    self.output_queue.put(("status", "❌ Erro ao dividir vídeo em segmentos"))
                    return
            else:
                segments = [self.video_path.get()]

            # Processar cada segmento individualmente
            for i, segment_path in enumerate(segments):
                self.output_queue.put(("status", f"🎬 Processando segmento {i+1}/{len(segments)}..."))

                # Construir comando
                cmd = [
                    "python3", "generateClips.py",
                    segment_path,
                    "--output-dir", self.output_dir.get(),
                    "--min-clips", str(self.min_clips.get()),
                    "--max-clips", str(self.max_clips.get()),
                    "--whisper-model", self.whisper_model.get()
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
                            progress_value = min(progress_value + 5, 70) # Incrementar gradualmente
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
                        elif "%" in output and any(word in output.lower() for word in ["progress", "processing", "complete"]):
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

    def check_queue(self):
        try:
            while True:
                msg_type, data = self.output_queue.get_nowait()

                if msg_type == "status":
                    self.status_label.configure(text=data)
                elif msg_type == "progress":
                    self.progress_bar['value'] = data
                elif msg_type == "log":
                    self.log_text.insert(tk.END, data)
                    self.log_text.see(tk.END)
                elif msg_type == "error":
                    messagebox.showerror("Erro", f"Erro durante o processamento:\n{data}")
                elif msg_type == "finished":
                    self.is_processing = False
                    self.process_button.configure(state="normal")
                    self.stop_button.configure(state="disabled")

                    if data:  # Sucesso
                        messagebox.showinfo("Sucesso", f"Processamento concluído com sucesso!\n\nOs clipes foram salvos em:\n{self.output_dir.get()}")
                        # Abrir pasta de saída
                        if messagebox.askyesno("Abrir Pasta", "Deseja abrir a pasta de saída?"):
                            self.open_output_folder()
                    else:  # Falha
                        messagebox.showerror("Erro", "O processamento falhou. Verifique o log para mais detalhes.")

        except queue.Empty:
            pass

        # Agendar próxima verificação
        self.root.after(100, self.check_queue)

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
