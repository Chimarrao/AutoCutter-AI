#!/usr/bin/env python3
"""
Script simples para testar TTS diretamente
"""
import sys
import os

# Adicionar src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_tts_direct():
    """Testar TTS diretamente sem GUI"""
    print("=== TESTANDO TTS DIRETAMENTE ===")

    try:
        from TTS.api import TTS
        import torch
        from pydub import AudioSegment
        import queue
        import re

        print("✅ Bibliotecas importadas com sucesso")

        # Simular classe com métodos necessários
        class MockGUI:
            def __init__(self):
                self.output_queue = queue.Queue()
                self.tts_device = "cpu"
                self.tts_model_loaded = False
                self.tts_model = None
                self.tts_text = "Olá! Este é um teste simples do sistema de conversão de texto para fala."
                self.tts_output_file = "teste_tts_direto.wav"
                self.output_dir = "output_folder"

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

            def load_tts_model(self):
                """Carrega o modelo TTS se não estiver carregado"""
                if self.tts_model_loaded and self.tts_model is not None:
                    return True

                try:
                    print("Carregando modelo XTTS v2...")

                    # Configurar torch para usar o dispositivo correto
                    if self.tts_device == "cuda" and torch.cuda.is_available():
                        torch.cuda.empty_cache()
                        device = "cuda"
                    else:
                        device = "cpu"

                    # Tentar carregar modelo com safe globals incluindo ambos os tipos necessários
                    try:
                        from TTS.tts.configs import xtts_config
                        from TTS.tts.models.xtts import XttsAudioConfig
                        print("Tentando carregar com safe globals (XttsConfig e XttsAudioConfig)...")
                        with torch.serialization.safe_globals([xtts_config.XttsConfig, XttsAudioConfig]):
                            self.tts_model = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", gpu=(device == "cuda"))
                    except Exception as e:
                        print(f"Falhou com safe globals: {e}")
                        print("Tentando com weights_only=False...")
                        # Fallback: tentar forçar weights_only=False (menos seguro, mas pode funcionar)
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
                            print(f"Falhou com weights_only=False: {e2}")
                            raise e  # Levantar erro original

                    self.tts_model.to(device)

                    self.tts_model_loaded = True
                    print("Modelo XTTS v2 carregado com sucesso!")
                    return True

                except Exception as e:
                    print(f"Erro ao carregar modelo TTS: {str(e)}")
                    return False

        # Criar mock GUI
        gui = MockGUI()

        # Testar carregamento do modelo
        if not gui.load_tts_model():
            print("❌ Falha ao carregar modelo")
            return False

        # Preparar texto
        print("Processando texto...")
        texto_limpo = gui.limpar_texto_tts(gui.tts_text)
        print(f"Texto limpo: {texto_limpo}")

        # Dividir em blocos
        blocos = gui.dividir_texto_tts(texto_limpo)
        print(f"Texto dividido em {len(blocos)} blocos: {blocos}")

        # Gerar áudio
        print("Gerando áudio...")
        final_audio = AudioSegment.silent(duration=0)

        for i, bloco in enumerate(blocos):
            if not bloco.strip():
                continue

            print(f"Gerando bloco {i+1}/{len(blocos)}: {bloco}")

            # Gerar áudio do bloco
            arquivo_temp = f"temp_tts_teste_{i}.wav"
            gui.tts_model.tts_to_file(
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

        # Salvar áudio final
        print(f"Salvando arquivo final: {gui.tts_output_file}")
        output_path = os.path.join(gui.output_dir, gui.tts_output_file)
        final_audio.export(output_path, format="wav")

        print(f"✅ TTS concluído! Arquivo salvo como: {output_path}")
        return True

    except Exception as e:
        print(f"❌ Erro geral: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testando TTS diretamente...")
    success = test_tts_direct()
    if success:
        print("\n🎉 TTS funcionando!")
    else:
        print("\n❌ TTS com problemas.")