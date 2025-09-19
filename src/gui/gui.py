#!/usr/bin/env python3
import sys
import os
import json
import queue
import threading
import subprocess
import tempfile
import io

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QProgressBar,
    QTabWidget, QGroupBox, QFormLayout, QSpinBox, QCheckBox,
    QFileDialog, QMessageBox, QComboBox, QListWidget, QSplitter,
    QFrame, QScrollArea, QRadioButton, QButtonGroup
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPalette, QColor

# Importar funções de processamento
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import processing
import transcription

# força UTF-8 como padrão (apenas se stdout estiver disponível)
# Nota: Esta configuração pode causar problemas em alguns ambientes
# if hasattr(sys.stdout, 'buffer') and sys.stdout.buffer is not None:
#     sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
# if hasattr(sys.stderr, 'buffer') and sys.stderr.buffer is not None:
#     sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUTF8"] = "1"

class ClipGeneratorGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        print("ClipGeneratorGUI __init__ called")

        # Arquivo de configuração
        self.config_file = os.path.join(os.path.dirname(__file__), '..', '..', 'user_config.json')

        # Carregar configurações salvas
        self.load_config()

        # Aplicar configurações carregadas
        self.theme = self.saved_theme
        self.font_size = self.saved_font_size

        # Variáveis para a aba básica (geração de clipes)
        self.video_path = ""
        self.youtube_url = ""
        self.output_dir = "saida"
        self.min_clips = 3
        self.max_clips = 8
        self.whisper_model = "base"
        self.api_key = self.saved_api_key
        self.captions = True
        self.no_review = True
        self.max_segment_duration = 30
        self.temp_dir = os.path.join(os.path.dirname(__file__), '..', '..', "temp")
        self.downloads_dir = os.path.join(os.path.dirname(__file__), '..', '..', "downloads")
        self.bulk_download_dir = os.path.join(os.path.dirname(__file__), '..', '..', "bulk_download")
        self.is_downloading = False
        self.mode = "clips"
        self.bulk_urls = ""

        # Variáveis separadas para o Vídeo Maker
        self.vm_video_path = ""
        self.vm_personagens = ""
        self.vm_texto_thumb = ""
        self.vm_sponsor_block = True
        self.vm_black_bars = True
        self.vm_black_bars_height = 170
        self.vm_cut_last_seconds = True
        self.vm_cut_seconds = 20
        self.vm_quality = "1080p 30fps"
        self.vm_video_title = None
        self.vm_video_id = None
        self.vm_is_processing = False

        # Fila para comunicação entre threads
        self.output_queue = queue.Queue()
        self.process = None
        self.is_processing = False

        # Variáveis para transcrição
        self.transcription_video_path = ""
        self.transcription_segments = []
        self.transcription_text = ""

        # Criar diretórios necessários
        self.create_directories()

        # Configurar interface
        self.setup_ui()

        # Iniciar verificação de fila
        self.check_queue()

    def load_config(self):
        """Carregar configurações do usuário"""
        self.saved_api_key = ""
        self.saved_theme = "light"  # padrão light
        self.saved_font_size = 10  # padrão 10
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.saved_api_key = config.get('api_key', '')
                    self.saved_theme = config.get('theme', 'light')
                    self.saved_font_size = config.get('font_size', 10)
        except Exception as e:
            print(f"Erro ao carregar configuração: {e}")

    def save_config(self):
        """Salvar configurações do usuário"""
        try:
            config = {
                'api_key': self.api_key,
                'theme': self.theme,
                'font_size': self.font_size
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            print(f"Erro ao salvar configuração: {e}")

    def apply_theme(self):
        """Aplicar o tema selecionado"""
        app = QApplication.instance()
        if self.theme == "dark":
            # Tema escuro
            app.setStyle("Fusion")
            dark_palette = QPalette()
            dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
            dark_palette.setColor(QPalette.WindowText, Qt.white)
            dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
            dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
            dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
            dark_palette.setColor(QPalette.ToolTipText, Qt.white)
            dark_palette.setColor(QPalette.Text, Qt.white)
            dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
            dark_palette.setColor(QPalette.ButtonText, Qt.white)
            dark_palette.setColor(QPalette.BrightText, Qt.red)
            dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
            dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
            dark_palette.setColor(QPalette.HighlightedText, Qt.black)
            app.setPalette(dark_palette)
        else:
            # Tema claro
            app.setStyle("Fusion")
            light_palette = QPalette()
            app.setPalette(light_palette)

    def apply_font_size(self):
        """Aplicar o tamanho da fonte"""
        font = QFont()
        font.setPointSize(self.font_size)
        app = QApplication.instance()
        app.setFont(font)

    def change_theme(self, theme):
        """Mudar o tema"""
        self.theme = theme
        self.apply_theme()
        self.save_config()

    def change_font_size(self, size):
        """Mudar o tamanho da fonte"""
        self.font_size = size
        self.apply_font_size()
        self.save_config()

    def create_directories(self):
        """Criar todas as pastas necessárias automaticamente"""
        directories = [
            self.output_dir,
            self.temp_dir,
            self.downloads_dir,
            self.bulk_download_dir,
            "saida"
        ]

        for directory in directories:
            try:
                os.makedirs(directory, exist_ok=True)
                print(f"Pasta criada/verificada: {directory}")
            except Exception as e:
                print(f"Erro ao criar pasta {directory}: {e}")

    def setup_ui(self):
        # Aplicar configurações de tema e fonte
        self.apply_theme()
        self.apply_font_size()

        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout principal
        main_layout = QVBoxLayout(central_widget)

        # Título
        title_label = QLabel("🎬 Gerador de Clipes com IA")
        title_font = QFont("Arial", 24, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        # Subtitle
        subtitle_label = QLabel("Transforme seus vídeos em clipes curtos automaticamente")
        subtitle_font = QFont("Arial", 12)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(subtitle_label)

        # Tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # Criar as abas
        self.setup_basic_tab()
        self.setup_bulk_download_tab()
        self.setup_advanced_tab()
        self.setup_processing_tab()
        self.setup_video_maker_tab()
        self.setup_transcription_tab()

    def setup_basic_tab(self):
        # Frame da aba básica
        basic_widget = QWidget()
        self.tab_widget.addTab(basic_widget, "📁 Básico")

        # Layout
        layout = QVBoxLayout(basic_widget)

        # Scroll area
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # Seleção de vídeo
        video_group = QGroupBox("📹 Arquivo de Vídeo")
        video_layout = QVBoxLayout(video_group)

        self.video_entry = QLineEdit()
        self.video_entry.setPlaceholderText("Selecione um arquivo de vídeo...")
        video_layout.addWidget(self.video_entry)

        browse_video_btn = QPushButton("📂 Navegar")
        browse_video_btn.clicked.connect(self.browse_video)
        video_layout.addWidget(browse_video_btn)

        scroll_layout.addWidget(video_group)

        # Pasta de saída
        output_group = QGroupBox("📁 Pasta de Saída")
        output_layout = QVBoxLayout(output_group)

        self.output_entry = QLineEdit(self.output_dir)
        output_layout.addWidget(self.output_entry)

        browse_output_btn = QPushButton("📂 Navegar")
        browse_output_btn.clicked.connect(self.browse_output)
        output_layout.addWidget(browse_output_btn)

        scroll_layout.addWidget(output_group)

        # Configurações de clipes
        clips_group = QGroupBox("🎯 Configurações de Clipes")
        clips_layout = QFormLayout(clips_group)

        self.min_clips_spin = QSpinBox()
        self.min_clips_spin.setValue(self.min_clips)
        self.min_clips_spin.setRange(1, 20)
        clips_layout.addRow("Mínimo de clipes:", self.min_clips_spin)

        self.max_clips_spin = QSpinBox()
        self.max_clips_spin.setValue(self.max_clips)
        self.max_clips_spin.setRange(1, 20)
        clips_layout.addRow("Máximo de clipes:", self.max_clips_spin)

        self.whisper_combo = QComboBox()
        self.whisper_combo.addItems(["tiny", "base", "small", "medium", "large"])
        self.whisper_combo.setCurrentText(self.whisper_model)
        clips_layout.addRow("Modelo Whisper:", self.whisper_combo)

        self.api_key_entry = QLineEdit(self.api_key)
        self.api_key_entry.setEchoMode(QLineEdit.Password)
        clips_layout.addRow("API Key:", self.api_key_entry)

        self.captions_check = QCheckBox("Gerar legendas")
        self.captions_check.setChecked(self.captions)
        clips_layout.addRow(self.captions_check)

        scroll_layout.addWidget(clips_group)

        # Configurações da Interface
        interface_group = QGroupBox("🎨 Interface")
        interface_layout = QFormLayout(interface_group)

        # Tema
        theme_layout = QHBoxLayout()
        self.theme_group = QButtonGroup()

        self.light_radio = QRadioButton("Claro")
        self.light_radio.clicked.connect(lambda: self.change_theme("light"))
        self.theme_group.addButton(self.light_radio)
        theme_layout.addWidget(self.light_radio)

        self.dark_radio = QRadioButton("Escuro")
        self.dark_radio.clicked.connect(lambda: self.change_theme("dark"))
        self.theme_group.addButton(self.dark_radio)
        theme_layout.addWidget(self.dark_radio)

        # Definir o radio button correto baseado no tema atual
        if self.theme == "light":
            self.light_radio.setChecked(True)
        else:
            self.dark_radio.setChecked(True)

        interface_layout.addRow("Tema:", theme_layout)

        # Tamanho da fonte
        self.font_size_combo = QComboBox()
        self.font_size_combo.addItems(["10", "12", "14", "16", "18", "20"])
        self.font_size_combo.setCurrentText(str(self.font_size))
        self.font_size_combo.currentTextChanged.connect(lambda size: self.change_font_size(int(size)))
        interface_layout.addRow("Tamanho da fonte:", self.font_size_combo)

        scroll_layout.addWidget(interface_group)

        # Botão processar
        self.process_btn = QPushButton("🚀 Processar Vídeo")
        self.process_btn.clicked.connect(self.start_processing)
        scroll_layout.addWidget(self.process_btn)

        # Progress
        self.progress_bar = QProgressBar()
        scroll_layout.addWidget(self.progress_bar)

        # Log
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(200)
        scroll_layout.addWidget(self.log_text)

        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)

    def setup_bulk_download_tab(self):
        # Implementar aba de download em massa
        bulk_widget = QWidget()
        self.tab_widget.addTab(bulk_widget, "📥 Download YouTube")

        layout = QVBoxLayout(bulk_widget)

        # URLs
        urls_group = QGroupBox("URLs para Download")
        urls_layout = QVBoxLayout(urls_group)

        self.bulk_urls_text = QTextEdit()
        self.bulk_urls_text.setPlaceholderText("Cole múltiplas URLs do YouTube, uma por linha...")
        urls_layout.addWidget(self.bulk_urls_text)

        clear_btn = QPushButton("🗑️ Limpar")
        clear_btn.clicked.connect(self.clear_bulk_urls)
        urls_layout.addWidget(clear_btn)

        layout.addWidget(urls_group)

        # Pasta de destino
        folder_group = QGroupBox("Pasta de Destino")
        folder_layout = QVBoxLayout(folder_group)

        self.bulk_folder_entry = QLineEdit(self.bulk_download_dir)
        folder_layout.addWidget(self.bulk_folder_entry)

        browse_bulk_btn = QPushButton("📂 Navegar")
        browse_bulk_btn.clicked.connect(self.browse_bulk_folder)
        folder_layout.addWidget(browse_bulk_btn)

        layout.addWidget(folder_group)

        # Qualidade
        quality_group = QGroupBox("Qualidade")
        quality_layout = QVBoxLayout(quality_group)

        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["best", "1080p", "720p", "480p", "360p"])
        quality_layout.addWidget(self.quality_combo)

        layout.addWidget(quality_group)

        # Botão download
        self.bulk_download_btn = QPushButton("📥 Iniciar Download em Massa")
        self.bulk_download_btn.clicked.connect(self.start_bulk_download)
        layout.addWidget(self.bulk_download_btn)

        # Progress
        self.bulk_progress = QProgressBar()
        layout.addWidget(self.bulk_progress)

        # Log
        self.bulk_log = QTextEdit()
        layout.addWidget(self.bulk_log)

    def setup_advanced_tab(self):
        advanced_widget = QWidget()
        self.tab_widget.addTab(advanced_widget, "⚙️ Avançado")

        layout = QVBoxLayout(advanced_widget)

        # Duração máxima
        duration_group = QGroupBox("Duração de Segmentos")
        duration_layout = QVBoxLayout(duration_group)

        self.max_duration_spin = QSpinBox()
        self.max_duration_spin.setValue(self.max_segment_duration)
        self.max_duration_spin.setRange(10, 120)
        self.max_duration_spin.setSuffix(" minutos")
        duration_layout.addWidget(QLabel("Duração máxima do segmento:"))
        duration_layout.addWidget(self.max_duration_spin)

        layout.addWidget(duration_group)

        # Pasta temporária
        temp_group = QGroupBox("Pasta Temporária")
        temp_layout = QVBoxLayout(temp_group)

        self.temp_entry = QLineEdit(self.temp_dir)
        temp_layout.addWidget(self.temp_entry)

        browse_temp_btn = QPushButton("📂 Navegar")
        browse_temp_btn.clicked.connect(self.browse_temp)
        temp_layout.addWidget(browse_temp_btn)

        layout.addWidget(temp_group)

        # GPU/CPU
        gpu_group = QGroupBox("Processamento GPU/CPU")
        gpu_layout = QVBoxLayout(gpu_group)

        self.gpu_combo = QComboBox()
        self.gpu_combo.addItems(["CPU", "NVIDIA CUDA", "AMD VAAPI"])
        gpu_layout.addWidget(QLabel("Selecionar acelerador:"))
        gpu_layout.addWidget(self.gpu_combo)

        # Lista de dispositivos
        self.device_list = QListWidget()
        self.device_list.addItem("Clique em 'Detectar Dispositivos' para ver os disponíveis")
        gpu_layout.addWidget(QLabel("Dispositivos detectados:"))
        gpu_layout.addWidget(self.device_list)

        # Barra de progresso para detecção
        self.device_progress = QProgressBar()
        self.device_progress.setVisible(False)
        gpu_layout.addWidget(self.device_progress)

        detect_btn = QPushButton("🔍 Detectar Dispositivos")
        detect_btn.clicked.connect(self.start_device_detection)
        gpu_layout.addWidget(detect_btn)

        layout.addWidget(gpu_group)

    def setup_processing_tab(self):
        processing_widget = QWidget()
        self.tab_widget.addTab(processing_widget, "🎥 Processamento")

        layout = QVBoxLayout(processing_widget)

        # Status
        status_label = QLabel("Status do processamento FFmpeg")
        layout.addWidget(status_label)

        self.processing_log = QTextEdit()
        layout.addWidget(self.processing_log)

    def setup_video_maker_tab(self):
        vm_widget = QWidget()
        self.tab_widget.addTab(vm_widget, "🎬 Vídeo Maker")

        layout = QVBoxLayout(vm_widget)

        # Arquivo de vídeo
        video_group = QGroupBox("Vídeo de Entrada")
        video_layout = QVBoxLayout(video_group)

        self.vm_video_entry = QLineEdit()
        self.vm_video_entry.setPlaceholderText("Selecione um vídeo...")
        video_layout.addWidget(self.vm_video_entry)

        browse_vm_btn = QPushButton("📂 Navegar")
        browse_vm_btn.clicked.connect(self.browse_vm_video)
        video_layout.addWidget(browse_vm_btn)

        layout.addWidget(video_group)

        # Configurações
        config_group = QGroupBox("Configurações")
        config_layout = QFormLayout(config_group)

        self.vm_personagens_entry = QLineEdit()
        config_layout.addRow("Personagens:", self.vm_personagens_entry)

        self.vm_thumb_entry = QLineEdit()
        config_layout.addRow("Texto Thumbnail:", self.vm_thumb_entry)

        self.vm_sponsor_check = QCheckBox("Remover Sponsor Block")
        self.vm_sponsor_check.setChecked(self.vm_sponsor_block)
        config_layout.addRow(self.vm_sponsor_check)

        self.vm_bars_check = QCheckBox("Adicionar Barras Pretas")
        self.vm_bars_check.setChecked(self.vm_black_bars)
        config_layout.addRow(self.vm_bars_check)

        self.vm_bars_height_spin = QSpinBox()
        self.vm_bars_height_spin.setValue(self.vm_black_bars_height)
        config_layout.addRow("Altura Barras:", self.vm_bars_height_spin)

        self.vm_cut_check = QCheckBox("Cortar Últimos Segundos")
        self.vm_cut_check.setChecked(self.vm_cut_last_seconds)
        config_layout.addRow(self.vm_cut_check)

        self.vm_cut_spin = QSpinBox()
        self.vm_cut_spin.setValue(self.vm_cut_seconds)
        config_layout.addRow("Segundos a Cortar:", self.vm_cut_spin)

        self.vm_quality_combo = QComboBox()
        self.vm_quality_combo.addItems(["4K 30fps", "1080p 60fps", "1080p 30fps", "720p 60fps", "720p 30fps", "480p 30fps"])
        self.vm_quality_combo.setCurrentText(self.vm_quality)
        config_layout.addRow("Qualidade:", self.vm_quality_combo)

        layout.addWidget(config_group)

        # Explicação sobre conversões
        explanation_group = QGroupBox("Sobre as Conversões")
        explanation_layout = QVBoxLayout(explanation_group)

        explanation_label = QLabel("As conversões abaixo geram arquivos de vídeo no formato 9x16 (ideal para Shorts/YouTube) com uma caixa de texto posicionada.")
        explanation_label.setWordWrap(True)
        explanation_layout.addWidget(explanation_label)

        layout.addWidget(explanation_group)

        # Botões de conversão
        convert_group = QGroupBox("Conversões")
        convert_layout = QHBoxLayout(convert_group)

        centro_btn = QPushButton("📐 Centro")
        centro_btn.clicked.connect(lambda: self.converter_video("centro"))
        convert_layout.addWidget(centro_btn)

        esquerda_btn = QPushButton("⬅️ Esquerda")
        esquerda_btn.clicked.connect(lambda: self.converter_video("esquerda"))
        convert_layout.addWidget(esquerda_btn)

        direita_btn = QPushButton("➡️ Direita")
        direita_btn.clicked.connect(lambda: self.converter_video("direita"))
        convert_layout.addWidget(direita_btn)

        layout.addWidget(convert_group)

        # Progress
        self.vm_progress = QProgressBar()
        layout.addWidget(self.vm_progress)

        # Log
        self.vm_log = QTextEdit()
        layout.addWidget(self.vm_log)

    # Métodos de navegação
    def browse_video(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Selecionar Vídeo", "", "Vídeos (*.mp4 *.avi *.mkv *.mov)")
        if file_path:
            self.video_entry.setText(file_path)
            self.video_path = file_path

    def browse_vm_video(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Selecionar Vídeo", "", "Vídeos (*.mp4 *.avi *.mkv *.mov)")
        if file_path:
            self.vm_video_entry.setText(file_path)
            self.vm_video_path = file_path

    def browse_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Selecionar Pasta de Saída")
        if folder:
            self.output_entry.setText(folder)
            self.output_dir = folder

    def browse_temp(self):
        folder = QFileDialog.getExistingDirectory(self, "Selecionar Pasta Temporária")
        if folder:
            self.temp_entry.setText(folder)
            self.temp_dir = folder

    def browse_bulk_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Selecionar Pasta para Downloads")
        if folder:
            self.bulk_folder_entry.setText(folder)
            self.bulk_download_dir = folder

    def clear_bulk_urls(self):
        self.bulk_urls_text.clear()

    def start_bulk_download(self):
        """Iniciar download em massa de vídeos"""
        processing.start_bulk_download(self)

    def start_processing(self):
        """Iniciar processamento de vídeo"""
        processing.start_processing(self)

    def start_device_detection(self):
        """Iniciar detecção de dispositivos em thread separada"""
        self.device_list.clear()
        self.device_list.addItem("Detectando dispositivos...")
        self.device_progress.setVisible(True)
        self.device_progress.setValue(0)

        # Iniciar thread de detecção
        thread = threading.Thread(target=processing.detect_devices_thread, args=(self,), daemon=True)
        thread.start()

    def process_thread_messages(self):
        """Processar mensagens da fila de saída da thread"""
        try:
            while not self.output_queue.empty():
                message_type, data = self.output_queue.get_nowait()

                if message_type == "progress":
                    self.progress_bar.setValue(data)
                elif message_type == "log":
                    self.log_text.append(data.strip())
                elif message_type == "error":
                    QMessageBox.critical(self, "Erro", data)
                    self.process_btn.setEnabled(True)
                elif message_type == "finished":
                    self.process_btn.setEnabled(True)
                    if data:  # Sucesso
                        QMessageBox.information(self, "Processamento Concluído",
                                              "Geração de clipes concluída com sucesso!")
                        # Voltar para aba básica
                        self.tab_widget.setCurrentIndex(0)
                elif message_type == "bulk_progress":
                    self.bulk_progress.setValue(data)
                elif message_type == "bulk_log":
                    self.bulk_log.append(data.strip())
                elif message_type == "bulk_status":
                    # Atualizar status na aba de processamento
                    if hasattr(self, 'processing_log'):
                        self.processing_log.append(f"Status: {data}")
                elif message_type == "bulk_download_finished":
                    self.is_downloading = False
                    self.bulk_download_btn.setEnabled(True)
                    if data:  # Sucesso
                        QMessageBox.information(self, "Download em Massa Concluído",
                                              f"Download em massa concluído!\n\nOs arquivos foram salvos em:\n{self.bulk_download_dir}")
                        # Voltar para a aba de download em massa
                        self.tab_widget.setCurrentIndex(1)
                    else:  # Falha
                        QMessageBox.critical(self, "Erro", "O download em massa falhou. Verifique o log para mais detalhes.")
                elif message_type == "device_progress":
                    self.device_progress.setValue(data)
                elif message_type == "device_status":
                    # Atualizar o último item da lista com status
                    if self.device_list.count() > 0:
                        self.device_list.item(self.device_list.count() - 1).setText(data)
                elif message_type == "device_list":
                    # Limpar lista e adicionar dispositivos detectados
                    self.device_list.clear()
                    for device in data:
                        self.device_list.addItem(device)
                    # Esconder barra de progresso
                    self.device_progress.setVisible(False)
                elif message_type == "device_error":
                    self.device_list.clear()
                    self.device_list.addItem(f"Erro: {data}")
                    self.device_progress.setVisible(False)
                elif message_type == "transcription_progress":
                    if hasattr(self, 'transcription_progress'):
                        self.transcription_progress.setValue(data)
                elif message_type == "transcription_status":
                    if hasattr(self, 'transcription_status_label'):
                        self.transcription_status_label.setText(data)
                elif message_type == "transcription_result":
                    self.display_transcription_results(data)
                elif message_type == "transcription_error":
                    QMessageBox.critical(self, "Erro na Transcrição", data)
                elif message_type == "render_status":
                    if hasattr(self, 'render_status_label'):
                        self.render_status_label.setText(data)
                elif message_type == "render_error":
                    QMessageBox.critical(self, "Erro na Renderização", data)
                elif message_type == "render_success":
                    QMessageBox.information(self, "Renderização Concluída",
                                          f"Vídeo com legendas criado com sucesso!\n\nArquivo: {data}")
        except:
            pass

    def converter_video(self, tipo):
        # Implementar conversão
        pass

    def setup_transcription_tab(self):
        """Configurar aba de transcrição e legendas"""
        transcription_widget = QWidget()
        self.tab_widget.addTab(transcription_widget, "📝 Transcrição")

        layout = QVBoxLayout(transcription_widget)

        # Verificação de FFmpeg
        ffmpeg_group = QGroupBox("🔧 Verificação de Dependências")
        ffmpeg_layout = QVBoxLayout(ffmpeg_group)

        self.ffmpeg_status_label = QLabel("Verificando FFmpeg...")
        ffmpeg_layout.addWidget(self.ffmpeg_status_label)

        check_ffmpeg_btn = QPushButton("🔍 Verificar FFmpeg")
        check_ffmpeg_btn.clicked.connect(self.check_ffmpeg_status)
        ffmpeg_layout.addWidget(check_ffmpeg_btn)

        layout.addWidget(ffmpeg_group)

        # Seleção de vídeo
        video_group = QGroupBox("📹 Arquivo de Vídeo")
        video_layout = QVBoxLayout(video_group)

        self.transcription_video_entry = QLineEdit()
        self.transcription_video_entry.setPlaceholderText("Selecione um vídeo para transcrição...")
        video_layout.addWidget(self.transcription_video_entry)

        browse_transcription_btn = QPushButton("📂 Navegar")
        browse_transcription_btn.clicked.connect(self.browse_transcription_video)
        video_layout.addWidget(browse_transcription_btn)

        layout.addWidget(video_group)

        # Configurações de transcrição
        config_group = QGroupBox("⚙️ Configurações de Transcrição")
        config_layout = QFormLayout(config_group)

        self.transcription_model_combo = QComboBox()
        self.transcription_model_combo.addItems(["tiny", "base", "small", "medium", "large"])
        self.transcription_model_combo.setCurrentText("base")
        config_layout.addRow("Modelo Whisper:", self.transcription_model_combo)

        self.transcription_gpu_check = QCheckBox("Usar GPU (CUDA)")
        config_layout.addRow(self.transcription_gpu_check)

        layout.addWidget(config_group)

        # Botão de transcrição
        self.transcription_btn = QPushButton("🎤 Iniciar Transcrição")
        self.transcription_btn.clicked.connect(self.start_transcription)
        layout.addWidget(self.transcription_btn)

        # Progress e status
        self.transcription_progress = QProgressBar()
        layout.addWidget(self.transcription_progress)

        self.transcription_status_label = QLabel("Aguardando...")
        layout.addWidget(self.transcription_status_label)

        # Resultados da transcrição
        results_group = QGroupBox("📋 Resultados da Transcrição")
        results_layout = QVBoxLayout(results_group)

        # Área de texto para segmentos
        self.transcription_segments_text = QTextEdit()
        self.transcription_segments_text.setPlaceholderText("Os segmentos transcritos aparecerão aqui...")
        results_layout.addWidget(self.transcription_segments_text)

        # Botões de exportação
        export_layout = QHBoxLayout()

        copy_srt_btn = QPushButton("📄 Copiar SRT")
        copy_srt_btn.clicked.connect(self.copy_srt)
        export_layout.addWidget(copy_srt_btn)

        copy_ass_btn = QPushButton("🎭 Copiar ASS")
        copy_ass_btn.clicked.connect(self.copy_ass)
        export_layout.addWidget(copy_ass_btn)

        copy_text_btn = QPushButton("📝 Copiar Texto Puro")
        copy_text_btn.clicked.connect(self.copy_plain_text)
        export_layout.addWidget(copy_text_btn)

        results_layout.addLayout(export_layout)
        layout.addWidget(results_group)

        # Renderização com legendas
        render_group = QGroupBox("🎬 Renderizar com Legendas")
        render_layout = QFormLayout(render_group)

        self.render_quality_combo = QComboBox()
        self.render_quality_combo.addItems(["4K 30fps", "1080p 60fps", "1080p 30fps", "720p 60fps", "720p 30fps", "480p 30fps"])
        self.render_quality_combo.setCurrentText("1080p 30fps")
        render_layout.addRow("Qualidade:", self.render_quality_combo)

        render_layout.addRow(self.transcription_gpu_check)

        render_video_btn = QPushButton("🎬 Renderizar Vídeo")
        render_video_btn.clicked.connect(self.start_video_render)
        render_layout.addRow(render_video_btn)

        self.render_status_label = QLabel("Aguardando...")
        render_layout.addRow("Status:", self.render_status_label)

        layout.addWidget(render_group)

        # Verificar FFmpeg ao abrir a aba
        QTimer.singleShot(100, self.check_ffmpeg_status)

    def check_ffmpeg_status(self):
        """Verificar status do FFmpeg"""
        self.ffmpeg_status_label.setText("Verificando FFmpeg...")
        QApplication.processEvents()

        ffmpeg_ok, ffmpeg_msg = transcription.check_ffmpeg()
        if ffmpeg_ok:
            self.ffmpeg_status_label.setText(f"✅ FFmpeg OK: {ffmpeg_msg}")
        else:
            self.ffmpeg_status_label.setText(f"❌ FFmpeg: {ffmpeg_msg}")

    def browse_transcription_video(self):
        """Navegar para selecionar vídeo para transcrição"""
        file_path, _ = QFileDialog.getOpenFileName(self, "Selecionar Vídeo", "", "Vídeos (*.mp4 *.avi *.mkv *.mov)")
        if file_path:
            self.transcription_video_entry.setText(file_path)
            self.transcription_video_path = file_path

    def start_transcription(self):
        """Iniciar transcrição"""
        transcription.start_transcription(self)

    def display_transcription_results(self, segments):
        """Exibir resultados da transcrição"""
        result_text = ""
        for i, segment in enumerate(segments, 1):
            start_time = transcription.format_timestamp(segment['start'])
            end_time = transcription.format_timestamp(segment['end'])
            text = segment['text'].strip()

            result_text += f"{i}. [{start_time} --> {end_time}]\n{text}\n\n"

        self.transcription_segments_text.setText(result_text)

    def copy_srt(self):
        """Copiar legenda em formato SRT"""
        if not self.transcription_segments:
            QMessageBox.warning(self, "Aviso", "Execute a transcrição primeiro!")
            return

        srt_content = transcription.generate_srt(self.transcription_segments)
        QApplication.clipboard().setText(srt_content)
        QMessageBox.information(self, "Sucesso", "Legenda SRT copiada para a área de transferência!")

    def copy_ass(self):
        """Copiar legenda em formato ASS"""
        if not self.transcription_segments:
            QMessageBox.warning(self, "Aviso", "Execute a transcrição primeiro!")
            return

        ass_content = transcription.generate_ass(self.transcription_segments)
        QApplication.clipboard().setText(ass_content)
        QMessageBox.information(self, "Sucesso", "Legenda ASS copiada para a área de transferência!")

    def copy_plain_text(self):
        """Copiar texto puro da transcrição"""
        if not self.transcription_text:
            QMessageBox.warning(self, "Aviso", "Execute a transcrição primeiro!")
            return

        QApplication.clipboard().setText(self.transcription_text)
        QMessageBox.information(self, "Sucesso", "Texto puro copiado para a área de transferência!")

    def start_video_render(self):
        """Iniciar renderização de vídeo com legendas"""
        transcription.start_video_render(self)

    def check_queue(self):
        """Verificar fila de mensagens das threads usando QTimer"""
        self.process_thread_messages()

        # Agendar próxima verificação
        QTimer.singleShot(100, self.check_queue)

    def run(self):
        self.show()
        self.resize(1280, 720)

def main():
    # Verificar se é um teste de importação
    if len(sys.argv) > 1 and sys.argv[1] == "--test-import":
        if len(sys.argv) > 2:
            module_name = sys.argv[2].lower()
            try:
                if module_name == "pyqt5":
                    from PyQt5.QtWidgets import QApplication
                    print("PyQt5 importado com sucesso")
                elif module_name == "torch":
                    import torch
                    print(f"Torch importado com sucesso - CUDA: {torch.cuda.is_available()}")
                elif module_name == "whisper":
                    import whisper
                    print("Whisper importado com sucesso")
                else:
                    print(f"Modulo '{module_name}' nao reconhecido para teste")
                    sys.exit(1)
                print("Teste de importacao bem-sucedido!")
                sys.exit(0)
            except ImportError as e:
                print(f"Erro ao importar {module_name}: {e}")
                sys.exit(1)
            except Exception as e:
                print(f"Erro geral ao testar {module_name}: {e}")
                sys.exit(1)
        else:
            print("Uso: --test-import <modulo>")
            sys.exit(1)

    # Importar PyQt5 aqui para garantir que seja carregado no contexto do executável
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = ClipGeneratorGUI()
    window.run()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()