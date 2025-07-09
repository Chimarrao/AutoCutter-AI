#!/usr/bin/env python3
import customtkinter as ctk
from tkinter import filedialog, messagebox
import subprocess
import threading
import os
import json
import queue
import tempfile
import re

# Configurar aparência do CustomTkinter
ctk.set_appearance_mode("dark")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"


class ClipGeneratorGUI:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("🎬 Gerador de Clipes com IA")
        self.root.geometry("1280x900")
        self.root.resizable(True, True)

        # Arquivo de configuração
        self.config_file = os.path.join(os.path.dirname(__file__), 'user_config.json')

        # Carregar configurações salvas
        self.load_config()

        # Variáveis
        self.video_path = ctk.StringVar()
        self.output_dir = ctk.StringVar(value="output_folder")
        self.min_clips = ctk.IntVar(value=3)
        self.max_clips = ctk.IntVar(value=8)
        self.whisper_model = ctk.StringVar(value="base")
        self.api_key = ctk.StringVar(value=self.saved_api_key)
        self.captions = ctk.BooleanVar(value=True)
        self.no_review = ctk.BooleanVar(value=True)
        self.max_segment_duration = ctk.IntVar(value=30)
        self.temp_dir = ctk.StringVar(value=os.path.join(tempfile.gettempdir(), "video_segments"))

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
        # Frame principal
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Título
        title_label = ctk.CTkLabel(
            main_frame,
            text="🎬 Gerador de Clipes com IA",
            font=ctk.CTkFont(size=28, weight="bold")
        )
        title_label.pack(pady=(20, 10))

        # Subtitle
        subtitle_label = ctk.CTkLabel(
            main_frame,
            text="Transforme seus vídeos em clipes curtos automaticamente",
            font=ctk.CTkFont(size=16),
            text_color="gray70"
        )
        subtitle_label.pack(pady=(0, 30))

        # Tabview para organizar as configurações
        self.tabview = ctk.CTkTabview(main_frame)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=20)

        # Tabs
        self.tabview.add("📁 Básico")
        self.tabview.add("⚙️ Avançado")
        self.tabview.add("⚡ Processamento")

        # Setup tabs
        self.setup_basic_tab()
        self.setup_advanced_tab()
        self.setup_processing_tab()

        # Frame de botões
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x", padx=20, pady=20)

        # Botão processar
        self.process_button = ctk.CTkButton(
            button_frame,
            text="🚀 Processar Vídeo",
            command=self.start_processing,
            font=ctk.CTkFont(size=16, weight="bold"),
            height=50,
            width=200,
            fg_color="green",
            hover_color="darkgreen"
        )
        self.process_button.pack(side="left", padx=10, pady=10)

        # Botão parar
        self.stop_button = ctk.CTkButton(
            button_frame,
            text="⏹️ Parar",
            command=self.stop_processing,
            state="disabled",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=50,
            width=150,
            fg_color="red",
            hover_color="darkred"
        )
        self.stop_button.pack(side="right", padx=10, pady=10)

    def setup_basic_tab(self):
        # Frame da aba básica
        basic_frame = self.tabview.tab("📁 Básico")

        # Scrollable frame
        scrollable_frame = ctk.CTkScrollableFrame(basic_frame)
        scrollable_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Seleção de vídeo
        video_frame = ctk.CTkFrame(scrollable_frame)
        video_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            video_frame,
            text="📹 Arquivo de Vídeo",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=20, pady=(20, 10))

        video_input_frame = ctk.CTkFrame(video_frame)
        video_input_frame.pack(fill="x", padx=20, pady=(0, 20))

        self.video_entry = ctk.CTkEntry(
            video_input_frame,
            textvariable=self.video_path,
            placeholder_text="Selecione um arquivo de vídeo...",
            height=40,
            font=ctk.CTkFont(size=14)
        )
        self.video_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        ctk.CTkButton(
            video_input_frame,
            text="📂 Navegar",
            command=self.browse_video,
            width=120,
            height=40
        ).pack(side="right")

        # Pasta de saída
        output_frame = ctk.CTkFrame(scrollable_frame)
        output_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            output_frame,
            text="📁 Pasta de Saída",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=20, pady=(20, 10))

        output_input_frame = ctk.CTkFrame(output_frame)
        output_input_frame.pack(fill="x", padx=20, pady=(0, 20))

        self.output_entry = ctk.CTkEntry(
            output_input_frame,
            textvariable=self.output_dir,
            placeholder_text="Pasta onde os clipes serão salvos...",
            height=40,
            font=ctk.CTkFont(size=14)
        )
        self.output_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        ctk.CTkButton(
            output_input_frame,
            text="📂 Navegar",
            command=self.browse_output,
            width=120,
            height=40
        ).pack(side="right")

        # Número de clipes
        clips_frame = ctk.CTkFrame(scrollable_frame)
        clips_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            clips_frame,
            text="🎯 Quantidade de Clipes",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=20, pady=(20, 10))

        clips_config_frame = ctk.CTkFrame(clips_frame)
        clips_config_frame.pack(fill="x", padx=20, pady=(0, 20))

        # Min clips
        min_frame = ctk.CTkFrame(clips_config_frame)
        min_frame.pack(side="left", fill="x", expand=True, padx=(0, 10))

        ctk.CTkLabel(min_frame, text="Mínimo:", font=ctk.CTkFont(size=14)).pack(pady=(10, 5))
        self.min_spinbox = ctk.CTkEntry(min_frame, textvariable=self.min_clips, width=80, justify="center")
        self.min_spinbox.pack(pady=(0, 10))

        # Max clips
        max_frame = ctk.CTkFrame(clips_config_frame)
        max_frame.pack(side="right", fill="x", expand=True, padx=(10, 0))

        ctk.CTkLabel(max_frame, text="Máximo:", font=ctk.CTkFont(size=14)).pack(pady=(10, 5))
        self.max_spinbox = ctk.CTkEntry(max_frame, textvariable=self.max_clips, width=80, justify="center")
        self.max_spinbox.pack(pady=(0, 10))

    def setup_advanced_tab(self):
        # Frame da aba avançada
        advanced_frame = self.tabview.tab("⚙️ Avançado")

        # Scrollable frame
        scrollable_frame = ctk.CTkScrollableFrame(advanced_frame)
        scrollable_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Modelo Whisper
        whisper_frame = ctk.CTkFrame(scrollable_frame)
        whisper_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            whisper_frame,
            text="🎤 Modelo Whisper",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=20, pady=(20, 10))

        self.whisper_combo = ctk.CTkComboBox(
            whisper_frame,
            values=["tiny", "base", "small", "medium", "large"],
            variable=self.whisper_model,
            state="readonly",
            height=40,
            font=ctk.CTkFont(size=14)
        )
        self.whisper_combo.pack(fill="x", padx=20, pady=(0, 20))

        # API Key
        api_frame = ctk.CTkFrame(scrollable_frame)
        api_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            api_frame,
            text="🔑 Chave API do Google Gemini",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=20, pady=(20, 10))

        self.api_entry = ctk.CTkEntry(
            api_frame,
            textvariable=self.api_key,
            placeholder_text="Cole sua chave API aqui...",
            show="*",
            height=40,
            font=ctk.CTkFont(size=14)
        )
        self.api_entry.pack(fill="x", padx=20, pady=(0, 20))

        # Opções
        options_frame = ctk.CTkFrame(scrollable_frame)
        options_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            options_frame,
            text="🎛️ Opções",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=20, pady=(20, 10))

        # Checkbox para não revisar
        self.no_review_checkbox = ctk.CTkCheckBox(
            options_frame,
            text="Processar sem revisão manual",
            variable=self.no_review,
            font=ctk.CTkFont(size=14)
        )
        self.no_review_checkbox.pack(anchor="w", padx=20, pady=(0, 20))

        # Duração máxima do segmento
        duration_frame = ctk.CTkFrame(scrollable_frame)
        duration_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            duration_frame,
            text="⏱️ Duração Máxima do Segmento",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=20, pady=(20, 10))

        ctk.CTkLabel(
            duration_frame,
            text="Duração máxima de cada segmento em minutos:",
            font=ctk.CTkFont(size=14)
        ).pack(anchor="w", padx=20, pady=(0, 10))

        self.duration_spinbox = ctk.CTkEntry(
            duration_frame,
            textvariable=self.max_segment_duration,
            width=100,
            justify="center",
            height=40
        )
        self.duration_spinbox.pack(anchor="w", padx=20, pady=(0, 20))

        # Pasta temporária
        temp_frame = ctk.CTkFrame(scrollable_frame)
        temp_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            temp_frame,
            text="📂 Pasta Temporária",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=20, pady=(20, 10))

        ctk.CTkLabel(
            temp_frame,
            text="Pasta onde os segmentos de vídeo serão armazenados temporariamente:",
            font=ctk.CTkFont(size=14)
        ).pack(anchor="w", padx=20, pady=(0, 10))

        temp_input_frame = ctk.CTkFrame(temp_frame)
        temp_input_frame.pack(fill="x", padx=20, pady=(0, 20))

        self.temp_entry = ctk.CTkEntry(
            temp_input_frame,
            textvariable=self.temp_dir,
            placeholder_text="Pasta temporária...",
            height=40,
            font=ctk.CTkFont(size=14)
        )
        self.temp_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        ctk.CTkButton(
            temp_input_frame,
            text="📂 Navegar",
            command=self.browse_temp,
            width=120,
            height=40
        ).pack(side="right")

    def setup_processing_tab(self):
        # Frame da aba de processamento
        processing_frame = self.tabview.tab("⚡ Processamento")

        # Status
        status_frame = ctk.CTkFrame(processing_frame)
        status_frame.pack(fill="x", padx=20, pady=20)

        ctk.CTkLabel(
            status_frame,
            text="📊 Status",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=20, pady=(20, 10))

        self.status_label = ctk.CTkLabel(
            status_frame,
            text="Aguardando...",
            font=ctk.CTkFont(size=14),
            anchor="w"
        )
        self.status_label.pack(fill="x", padx=20, pady=(0, 20))

        # Barra de progresso
        progress_frame = ctk.CTkFrame(processing_frame)
        progress_frame.pack(fill="x", padx=20, pady=(0, 20))

        ctk.CTkLabel(
            progress_frame,
            text="📈 Progresso",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=20, pady=(20, 10))

        self.progress_bar = ctk.CTkProgressBar(progress_frame, height=20)
        self.progress_bar.pack(fill="x", padx=20, pady=(0, 20))
        self.progress_bar.set(0)

        # Log de saída
        log_frame = ctk.CTkFrame(processing_frame)
        log_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        ctk.CTkLabel(
            log_frame,
            text="📝 Log de Processamento",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=20, pady=(20, 10))

        # Text widget para o log
        self.log_text = ctk.CTkTextbox(
            log_frame,
            height=300,
            font=ctk.CTkFont(family="Consolas", size=12)
        )
        self.log_text.pack(fill="both", expand=True, padx=20, pady=(0, 20))

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
        self.progress_bar.set(0)
        self.log_text.delete("1.0", "end")

        # Mudar para a aba de processamento
        self.tabview.set("⚡ Processamento")

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

    def check_queue(self):
        try:
            while True:
                msg_type, data = self.output_queue.get_nowait()

                if msg_type == "status":
                    self.status_label.configure(text=data)
                elif msg_type == "progress":
                    self.progress_bar.set(data / 100)
                elif msg_type == "log":
                    self.log_text.insert("end", data)
                    self.log_text.see("end")
                elif msg_type == "error":
                    messagebox.showerror("Erro", f"Erro durante o processamento:\n{data}")
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
