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

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QProgressBar,
    QTabWidget, QGroupBox, QFormLayout, QSpinBox, QCheckBox,
    QFileDialog, QMessageBox, QComboBox, QListWidget, QSplitter,
    QFrame, QScrollArea, QRadioButton, QButtonGroup
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPalette, QColor

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


class ClipGeneratorGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎬 Gerador de Clipes com IA")
        self.setGeometry(100, 100, 1280, 900)

        # Arquivo de configuração
        self.config_file = os.path.join(os.path.dirname(__file__), '../../../user_config.json')

        # Carregar configurações salvas
        self.load_config()

        # Variáveis de configuração da interface
        self.theme = self.saved_theme  # "light" ou "dark"
        self.font_size = self.saved_font_size  # tamanho da fonte

        # Variáveis para a aba básica (geração de clipes)
        self.video_path = ""
        self.youtube_url = ""
        self.output_dir = "output_folder"
        self.min_clips = 3
        self.max_clips = 8
        self.whisper_model = "base"
        self.api_key = self.saved_api_key
        self.captions = True
        self.max_segment_duration = 30
        self.temp_dir = os.path.join(os.path.dirname(__file__), "../../../temp")
        self.downloads_dir = os.path.join(os.path.dirname(__file__), "../../../downloads")
        self.bulk_download_dir = os.path.join(os.path.dirname(__file__), "../../../bulk_download")
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

        # Variáveis para TTS
        self.tts_text = ""
        self.tts_output_file = ""
        self.tts_is_processing = False
        self.tts_model_loaded = False
        self.tts_model = None
        self.tts_device = "cuda"  # padrão GPU

        # Variáveis para geração de imagens
        self.image_prompt = ""
        self.image_output_dir = "output_folder"
        self.image_is_processing = False
        self.image_model_loaded = False
        self.image_model = None
        self.image_device = "cuda"  # padrão GPU

        # Fila para comunicação entre threads
        self.output_queue = queue.Queue()
        self.process = None
        self.is_processing = False

        # Criar pastas automaticamente
        self.create_directories()

        self.setup_ui()
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
                    self.saved_theme = config.get('theme', 'dark')
                    self.saved_font_size = config.get('font_size', 14)
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
            "prontos"
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
        self.setup_tts_tab()
        self.setup_image_tab()

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

    def setup_tts_tab(self):
        tts_widget = QWidget()
        self.tab_widget.addTab(tts_widget, "🗣️ TTS")

        layout = QVBoxLayout(tts_widget)

        # Explicação sobre carregamento do modelo
        info_group = QGroupBox("ℹ️ Informações")
        info_layout = QVBoxLayout(info_group)

        info_label = QLabel("A primeira geração pode demorar mais pois precisa carregar o modelo de IA.\nModelo usado: XTTS v2 (multilingual) - Speaker: Damien Black")
        info_label.setWordWrap(True)
        info_layout.addWidget(info_label)

        layout.addWidget(info_group)

        # Texto para TTS
        text_group = QGroupBox("📝 Texto para Conversão")
        text_layout = QVBoxLayout(text_group)

        self.tts_text_edit = QTextEdit()
        self.tts_text_edit.setPlaceholderText("Digite o texto que deseja converter em áudio (será dividido automaticamente em blocos)...")
        text_layout.addWidget(self.tts_text_edit)

        layout.addWidget(text_group)

        # Configurações
        config_group = QGroupBox("⚙️ Configurações")
        config_layout = QFormLayout(config_group)

        # Dispositivo (GPU/CPU)
        device_layout = QHBoxLayout()
        self.tts_device_group = QButtonGroup()

        self.tts_gpu_radio = QRadioButton("GPU (CUDA)")
        self.tts_gpu_radio.clicked.connect(lambda: self.set_tts_device("cuda"))
        self.tts_device_group.addButton(self.tts_gpu_radio)
        device_layout.addWidget(self.tts_gpu_radio)

        self.tts_cpu_radio = QRadioButton("CPU")
        self.tts_cpu_radio.clicked.connect(lambda: self.set_tts_device("cpu"))
        self.tts_device_group.addButton(self.tts_cpu_radio)
        device_layout.addWidget(self.tts_cpu_radio)

        # Definir GPU como padrão
        self.tts_gpu_radio.setChecked(True)

        config_layout.addRow("Processar via:", device_layout)

        layout.addWidget(config_group)

        # Arquivo de saída
        output_group = QGroupBox("📁 Arquivo de Saída")
        output_layout = QVBoxLayout(output_group)

        self.tts_output_entry = QLineEdit()
        self.tts_output_entry.setPlaceholderText("Nome do arquivo de saída (ex: audio_final.wav)")
        output_layout.addWidget(self.tts_output_entry)

        layout.addWidget(output_group)

        # Botão gerar TTS
        self.tts_generate_btn = QPushButton("🎵 Gerar Áudio TTS")
        self.tts_generate_btn.clicked.connect(self.start_tts_generation)
        layout.addWidget(self.tts_generate_btn)

        # Progress
        self.tts_progress = QProgressBar()
        self.tts_progress.setVisible(False)
        layout.addWidget(self.tts_progress)

        # Log
        self.tts_log = QTextEdit()
        self.tts_log.setMaximumHeight(150)
        layout.addWidget(self.tts_log)

    def setup_image_tab(self):
        image_widget = QWidget()
        self.tab_widget.addTab(image_widget, "🎨 Imagens IA")

        layout = QVBoxLayout(image_widget)

        # Explicação sobre carregamento do modelo
        info_group = QGroupBox("ℹ️ Informações")
        info_layout = QVBoxLayout(info_group)

        info_label = QLabel("A primeira geração pode demorar mais pois precisa carregar o modelo de IA.\nModelo usado: Stable Diffusion XL - Gera imagens em 1920x1080 (16:9)")
        info_label.setWordWrap(True)
        info_layout.addWidget(info_label)

        layout.addWidget(info_group)

        # Prompt para geração
        prompt_group = QGroupBox("📝 Prompt de Geração")
        prompt_layout = QVBoxLayout(prompt_group)

        self.image_prompt_edit = QTextEdit()
        self.image_prompt_edit.setPlaceholderText("Descreva a imagem que deseja gerar...")
        prompt_layout.addWidget(self.image_prompt_edit)

        layout.addWidget(prompt_group)

        # Configurações
        config_group = QGroupBox("⚙️ Configurações")
        config_layout = QFormLayout(config_group)

        # Dispositivo (GPU/CPU)
        device_layout = QHBoxLayout()
        self.image_device_group = QButtonGroup()

        self.image_gpu_radio = QRadioButton("GPU (CUDA)")
        self.image_gpu_radio.clicked.connect(lambda: self.set_image_device("cuda"))
        self.image_device_group.addButton(self.image_gpu_radio)
        device_layout.addWidget(self.image_gpu_radio)

        self.image_cpu_radio = QRadioButton("CPU")
        self.image_cpu_radio.clicked.connect(lambda: self.set_image_device("cpu"))
        self.image_device_group.addButton(self.image_cpu_radio)
        device_layout.addWidget(self.image_cpu_radio)

        # Definir GPU como padrão
        self.image_gpu_radio.setChecked(True)

        config_layout.addRow("Processar via:", device_layout)

        layout.addWidget(config_group)

        # Pasta de saída
        output_group = QGroupBox("Pasta de Saída")
        output_layout = QVBoxLayout(output_group)

        self.image_output_entry = QLineEdit(self.image_output_dir)
        output_layout.addWidget(self.image_output_entry)

        browse_image_output_btn = QPushButton("📂 Navegar")
        browse_image_output_btn.clicked.connect(self.browse_image_output)
        output_layout.addWidget(browse_image_output_btn)

        layout.addWidget(output_group)

        # Botão gerar imagem
        self.image_generate_btn = QPushButton("🎨 Gerar Imagem")
        self.image_generate_btn.clicked.connect(self.start_image_generation)
        layout.addWidget(self.image_generate_btn)

        # Progress
        self.image_progress = QProgressBar()
        self.image_progress.setVisible(False)
        layout.addWidget(self.image_progress)

        # Log
        self.image_log = QTextEdit()
        self.image_log.setMaximumHeight(150)
        layout.addWidget(self.image_log)

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

    def browse_image_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Selecionar Pasta para Imagens Geradas")
        if folder:
            self.image_output_entry.setText(folder)
            self.image_output_dir = folder

    def clear_bulk_urls(self):
        self.bulk_urls_text.clear()

    # Outros métodos (implementar)
    def download_youtube_video(self):
        # Implementar download
        pass

    def start_processing(self):
        # Implementar processamento
        pass

    def start_bulk_download(self):
        # Implementar download em massa
        pass

    def start_device_detection(self):
        """Iniciar detecção de dispositivos em thread separada"""
        self.device_list.clear()
        self.device_list.addItem("Detectando dispositivos...")
        self.device_progress.setVisible(True)
        self.device_progress.setValue(0)

        # Iniciar thread de detecção
        thread = threading.Thread(target=self.detect_devices_thread, daemon=True)
        thread.start()

    def detect_devices_thread(self):
        """Thread para detectar dispositivos com barra de progresso"""
        try:
            devices = []

            # Etapa 1: Detectar CPUs
            self.output_queue.put(("device_progress", 20))
            self.output_queue.put(("device_status", "Detectando CPU..."))
            try:
                import platform
                cpu_info = platform.processor()
                if cpu_info and cpu_info.strip():
                    devices.append(f"CPU: {cpu_info}")
                else:
                    devices.append("CPU: Disponível")
            except Exception as e:
                devices.append(f"CPU: Disponível (erro: {str(e)})")

            # Etapa 2: Detectar GPUs NVIDIA
            self.output_queue.put(("device_progress", 40))
            self.output_queue.put(("device_status", "Detectando GPUs NVIDIA..."))
            try:
                # Usar timeout mais curto e verificar se o comando existe
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

            # Etapa 3: Detectar GPUs AMD
            self.output_queue.put(("device_progress", 60))
            self.output_queue.put(("device_status", "Detectando GPUs AMD..."))
            try:
                result = subprocess.run(['rocminfo'], capture_output=True, text=True, timeout=3)
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

            # Etapa 4: Detectar via torch
            self.output_queue.put(("device_progress", 80))
            self.output_queue.put(("device_status", "Detectando via PyTorch..."))
            try:
                import torch
                if torch.cuda.is_available():
                    device_count = torch.cuda.device_count()
                    if device_count > 0:
                        for i in range(device_count):
                            name = torch.cuda.get_device_name(i)
                            devices.append(f"CUDA GPU {i}: {name}")
                    else:
                        devices.append("PyTorch CUDA: GPUs detectadas mas count=0")
                else:
                    devices.append("PyTorch CUDA: Não disponível")
            except ImportError:
                devices.append("PyTorch: Não instalado")
            except Exception as e:
                devices.append(f"PyTorch: Erro ({str(e)})")

            # Etapa 5: Finalizar
            self.output_queue.put(("device_progress", 100))
            self.output_queue.put(("device_status", "Detecção concluída"))

            if not devices:
                devices.append("Nenhum dispositivo detectado")

            # Atualizar lista na thread principal
            self.output_queue.put(("device_list", devices))

        except Exception as e:
            self.output_queue.put(("device_error", f"Erro geral na detecção: {str(e)}"))

    def process_thread_messages(self):
        """Processar mensagens da fila de saída da thread"""
        try:
            while not self.output_queue.empty():
                message_type, data = self.output_queue.get_nowait()

                if message_type == "device_progress":
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
                elif message_type == "tts_progress":
                    self.tts_progress.setValue(data)
                elif message_type == "tts_log":
                    self.tts_log.append(data)
                elif message_type == "tts_complete":
                    self.tts_progress.setVisible(False)
                    self.tts_generate_btn.setEnabled(True)
                    QMessageBox.information(self, "Sucesso", f"TTS gerado com sucesso!\nArquivo: {self.tts_output_file}")
                elif message_type == "tts_error":
                    self.tts_progress.setVisible(False)
                    self.tts_generate_btn.setEnabled(True)
                    QMessageBox.critical(self, "Erro", data)
                elif message_type == "image_progress":
                    self.image_progress.setValue(data)
                elif message_type == "image_log":
                    self.image_log.append(data)
                elif message_type == "image_complete":
                    self.image_progress.setVisible(False)
                    self.image_generate_btn.setEnabled(True)
                    QMessageBox.information(self, "Sucesso", "Imagem gerada com sucesso!")
                elif message_type == "image_error":
                    self.image_progress.setVisible(False)
                    self.image_generate_btn.setEnabled(True)
                    QMessageBox.critical(self, "Erro", data)
        except:
            pass

    def start_tts_generation(self):
        """Iniciar geração de TTS em thread separada"""
        text = self.tts_text_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Erro", "Digite um texto para converter em áudio.")
            return

        output_file = self.tts_output_entry.text().strip()
        if not output_file:
            output_file = "tts_output.mp3"
        if not output_file.endswith('.mp3'):
            output_file += '.mp3'

        self.tts_text = text
        self.tts_output_file = output_file

        # Mostrar barra de progresso
        self.tts_progress.setVisible(True)
        self.tts_progress.setValue(0)
        self.tts_generate_btn.setEnabled(False)
        self.tts_log.clear()
        self.tts_log.append("Iniciando geração de TTS...")

        # Iniciar thread de TTS
        thread = threading.Thread(target=self.generate_tts_thread, daemon=True)
        thread.start()

    def set_tts_device(self, device):
        """Define o dispositivo para TTS"""
        self.tts_device = device
        # Resetar modelo se dispositivo mudou
        if self.tts_model_loaded and self.tts_model is not None:
            try:
                del self.tts_model
                self.tts_model = None
                self.tts_model_loaded = False
            except:
                pass

    def load_tts_model(self):
        """Carrega o modelo TTS se não estiver carregado"""
        if self.tts_model_loaded and self.tts_model is not None:
            return True

        try:
            from TTS.api import TTS
            import torch

            self.output_queue.put(("tts_log", f"Carregando modelo XTTS v2 no {self.tts_device.upper()}..."))

            # Configurar torch para usar o dispositivo correto
            if self.tts_device == "cuda" and torch.cuda.is_available():
                torch.cuda.empty_cache()
                device = "cuda"
            else:
                device = "cpu"

            # Permitir carregamento seguro do modelo TTS usando contexto manager
            try:
                from TTS.tts.configs import xtts_config
                from TTS.tts.models.xtts import XttsAudioConfig
                with torch.serialization.safe_globals([xtts_config.XttsConfig, XttsAudioConfig]):
                    # Inicializar modelo dentro do contexto seguro
                    self.tts_model = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", gpu=(device == "cuda"))
            except Exception as e:
                # Fallback: tentar forçar weights_only=False
                try:
                    # Monkey patch temporário para forçar weights_only=False
                    original_load = torch.load
                    def patched_load(*args, **kwargs):
                        kwargs['weights_only'] = False
                        return original_load(*args, **kwargs)
                    torch.load = patched_load

                    self.tts_model = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", gpu=(device == "cuda"))

                    # Restaurar função original
                    torch.load = original_load
                except Exception as e2:
                    raise e  # Levantar erro original

            self.tts_model.to(device)

            self.tts_model_loaded = True
            self.output_queue.put(("tts_log", "Modelo XTTS v2 carregado com sucesso!"))
            return True

        except Exception as e:
            self.output_queue.put(("tts_error", f"Erro ao carregar modelo TTS: {str(e)}"))
            return False

    def limpar_texto_tts(self, texto):
        """Limpa o texto conforme tts.py"""
        import re

        # Remover emojis
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags (iOS)
            "\U00002700-\U000027BF"  # dingbats
            "\U0001f926-\U0001f937"  # gestures
            "\U00010000-\U0010ffff"  # other unicode
            "\u2640-\u2642"  # gender symbols
            "\u2600-\u2B55"  # misc symbols
            "\u200d"  # zero width joiner
            "\u23cf"  # eject symbol
            "\u23e9"  # fast forward
            "\u231a"  # watch
            "\ufe0f"  # variation selector
            "\u3030"  # wavy dash
            "]+",
            flags=re.UNICODE
        )
        texto = emoji_pattern.sub('', texto)

        # Remover traços longos
        texto = texto.replace('—', '').replace('–', '')

        # Remover pontos duplos
        texto = re.sub(r'\.{2,}', '', texto)

        # Troca ponto por quebra de linha
        texto = texto.replace('.', '\n')

        # Manter apenas caracteres alfanuméricos, espaços e pontuação básica
        texto = re.sub(r'[^\w\s.,!?]', '', texto)

        return texto.strip()

    def dividir_texto_tts(self, texto, limite=500):
        """Divide o texto em blocos por sentenças conforme tts.py"""
        import re

        # Dividir por sentenças
        sentencas = re.split(r'(?<=[.!?])\s+', texto)
        blocos = []
        bloco_atual = ""
        for sent in sentencas:
            sent = sent.strip()
            if not sent:
                continue
            if len(bloco_atual) + len(sent) + 1 <= limite:
                bloco_atual += " " + sent if bloco_atual else sent
            else:
                if bloco_atual:
                    blocos.append(bloco_atual)
                bloco_atual = sent
        if bloco_atual:
            blocos.append(bloco_atual)
        return blocos

    def generate_tts_thread(self):
        """Thread para gerar TTS com XTTS v2 conforme tts.py"""
        try:
            import os
            from pydub import AudioSegment

            # Etapa 1: Carregar modelo se necessário
            self.output_queue.put(("tts_progress", 5))
            if not self.load_tts_model():
                return

            # Etapa 2: Preparar texto
            self.output_queue.put(("tts_progress", 20))
            self.output_queue.put(("tts_log", "Processando texto..."))

            # Limpar o texto
            texto_limpo = self.limpar_texto_tts(self.tts_text)

            # Dividir em blocos
            blocos = self.dividir_texto_tts(texto_limpo)
            self.output_queue.put(("tts_log", f"Texto dividido em {len(blocos)} blocos"))

            # Etapa 3: Gerar áudio para cada bloco
            self.output_queue.put(("tts_progress", 40))
            final_audio = AudioSegment.silent(duration=0)

            for i, bloco in enumerate(blocos):
                if not bloco.strip():
                    continue

                progress = 40 + (50 * (i + 1) // len(blocos))
                self.output_queue.put(("tts_progress", progress))
                self.output_queue.put(("tts_log", f"Gerando bloco {i+1}/{len(blocos)}..."))

                # Gerar áudio do bloco
                arquivo_temp = f"temp_tts_{i}.wav"
                self.tts_model.tts_to_file(
                    text=bloco,
                    speaker="Damien Black",
                    language="pt",
                    file_path=arquivo_temp,
                    speed=0.95
                )

                # Carregar e adicionar ao áudio final
                audio_segment = AudioSegment.from_wav(arquivo_temp)
                final_audio += audio_segment

                # Adicionar pausa entre blocos (300ms)
                if i < len(blocos) - 1:
                    final_audio += AudioSegment.silent(duration=300)

                # Remover arquivo temporário
                if os.path.exists(arquivo_temp):
                    os.remove(arquivo_temp)

            # Etapa 4: Salvar áudio final
            self.output_queue.put(("tts_progress", 95))
            self.output_queue.put(("tts_log", f"Salvando arquivo final: {self.tts_output_file}"))

            output_path = os.path.join(self.output_dir, self.tts_output_file)
            final_audio.export(output_path, format="wav")

            self.output_queue.put(("tts_progress", 100))
            self.output_queue.put(("tts_log", f"TTS concluído! Arquivo salvo como: {output_path}"))
            self.output_queue.put(("tts_complete", True))

        except ImportError as ie:
            self.output_queue.put(("tts_error", f"Bibliotecas necessárias não instaladas: {str(ie)}. Instale com: pip install TTS pydub"))
        except Exception as e:
            self.output_queue.put(("tts_error", f"Erro na geração de TTS: {str(e)}"))

    def start_image_generation(self):
        """Iniciar geração de imagem em thread separada"""
        prompt = self.image_prompt_edit.toPlainText().strip()
        if not prompt:
            QMessageBox.warning(self, "Erro", "Digite um prompt para gerar a imagem.")
            return

        self.image_prompt = prompt
        self.image_output_dir = self.image_output_entry.text().strip()

        # Mostrar barra de progresso
        self.image_progress.setVisible(True)
        self.image_progress.setValue(0)
        self.image_generate_btn.setEnabled(False)
        self.image_log.clear()
        self.image_log.append("Iniciando geração de imagem...")

        # Iniciar thread de geração de imagem
        thread = threading.Thread(target=self.generate_image_thread, daemon=True)
        thread.start()

    def set_image_device(self, device):
        """Define o dispositivo para geração de imagens"""
        self.image_device = device
        # Resetar modelo se dispositivo mudou
        if self.image_model_loaded and self.image_model is not None:
            try:
                del self.image_model
                self.image_model = None
                self.image_model_loaded = False
            except:
                pass

    def load_image_model(self):
        """Carrega o modelo Stable Diffusion XL se não estiver carregado"""
        if self.image_model_loaded and self.image_model is not None:
            return True

        try:
            from diffusers import StableDiffusionXLPipeline
            import torch

            self.output_queue.put(("image_log", f"Carregando Stable Diffusion XL no {self.image_device.upper()}..."))

            # Configurar dispositivo
            if self.image_device == "cuda" and torch.cuda.is_available():
                torch.cuda.empty_cache()
                device = "cuda"
                torch_dtype = torch.float16
            else:
                device = "cpu"
                torch_dtype = torch.float32

            # Carregar modelo SDXL
            model_name = "stabilityai/stable-diffusion-xl-base-1.0"
            self.image_model = StableDiffusionXLPipeline.from_pretrained(
                model_name,
                torch_dtype=torch_dtype
            ).to(device)

            self.image_model_loaded = True
            self.output_queue.put(("image_log", "Stable Diffusion XL carregado com sucesso!"))
            return True

        except Exception as e:
            self.output_queue.put(("image_error", f"Erro ao carregar modelo de imagem: {str(e)}"))
            return False

    def generate_image_thread(self):
        """Thread para gerar imagem com Stable Diffusion XL conforme img.py"""
        try:
            import os

            # Criar pasta de imagens se não existir
            os.makedirs("imagens", exist_ok=True)

            # Etapa 1: Carregar modelo se necessário
            self.output_queue.put(("image_progress", 5))
            if not self.load_image_model():
                return

            # Etapa 2: Preparar geração
            self.output_queue.put(("image_progress", 20))
            self.output_queue.put(("image_log", f"Prompt: {self.image_prompt[:50]}..."))

            # Etapa 3: Gerar imagem
            self.output_queue.put(("image_progress", 40))
            self.output_queue.put(("image_log", "Gerando imagem com Stable Diffusion XL..."))

            # Gerar imagem conforme img.py
            image = self.image_model(
                self.image_prompt,
                height=1080,         # altura 16:9
                width=1920,         # largura 16:9
                num_inference_steps=50,
                guidance_scale=7.5
            ).images[0]

            # Etapa 4: Salvar imagem
            self.output_queue.put(("image_progress", 90))
            self.output_queue.put(("image_log", "Salvando imagem..."))

            # Salvar na pasta imagens com nome sequencial
            import random
            image_number = random.randint(1, 1000)
            output_filename = f"{image_number}.png"
            output_path = os.path.join("imagens", output_filename)
            image.save(output_path)

            self.output_queue.put(("image_progress", 100))
            self.output_queue.put(("image_log", f"Imagem gerada com sucesso! Salva como: imagens/{output_filename}"))
            self.output_queue.put(("image_complete", True))

        except Exception as e:
            self.output_queue.put(("image_error", f"Erro na geração de imagem: {str(e)}"))

    def converter_video(self, tipo):
        # Implementar conversão
        pass

    def check_queue(self):
        """Verificar fila de mensagens das threads usando QTimer"""
        self.process_thread_messages()

        # Agendar próxima verificação
        QTimer.singleShot(100, self.check_queue)

    def run(self):
        self.show()


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
                elif module_name == "tts":
                    from TTS.api import TTS
                    print("TTS importado com sucesso")
                elif module_name == "diffusers":
                    from diffusers import StableDiffusionXLPipeline
                    print("Diffusers importado com sucesso")
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

    app = QApplication(sys.argv)
    window = ClipGeneratorGUI()
    window.run()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()