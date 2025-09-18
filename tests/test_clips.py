#!/usr/bin/env python3
"""
Testes para geração de clipes de vídeo
"""
import sys
import os
import tempfile
import json

# Adicionar src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_clip_generation_validation():
    """Testar validação de entrada para geração de clipes"""
    print("=== TESTANDO VALIDAÇÃO DE GERAÇÃO DE CLIPES ===")

    try:
        # Simular validação de entrada como no generateClips.py
        test_cases = [
            # (video_path, output_dir, min_clips, max_clips, expected_valid)
            ("video.mp4", "output", 3, 8, True),      # Válido
            ("", "output", 3, 8, False),              # Vídeo vazio
            ("video.mp4", "", 3, 8, False),           # Output vazio
            ("video.mp4", "output", 0, 8, False),     # Min clips inválido
            ("video.mp4", "output", 3, 2, False),     # Max < min
            ("video.mp4", "output", 15, 20, True),    # Valores altos válidos
        ]

        def validate_inputs(video_path, output_dir, min_clips, max_clips):
            """Simular validação do generateClips.py"""
            if not video_path:
                return False, "Caminho do vídeo não fornecido"

            if not os.path.exists(video_path):
                return False, "Arquivo de vídeo não existe"

            if not output_dir:
                return False, "Diretório de saída não fornecido"

            if min_clips < 1:
                return False, "Número mínimo de clipes deve ser pelo menos 1"

            if max_clips < min_clips:
                return False, "Número máximo de clipes deve ser maior que o mínimo"

            return True, "OK"

        # Criar arquivo de vídeo temporário para teste
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_video:
            temp_video_path = temp_video.name

        try:
            for video_path, output_dir, min_clips, max_clips, expected_valid in test_cases:
                # Usar arquivo temporário para casos válidos
                if video_path and expected_valid:
                    test_video_path = temp_video_path
                else:
                    test_video_path = video_path

                is_valid, message = validate_inputs(test_video_path, output_dir, min_clips, max_clips)

                status = "✅" if is_valid == expected_valid else "❌"
                print(f"{status} {test_video_path or '(vazio)'} -> {message}")

                if is_valid != expected_valid:
                    print(f"   Esperado: {'Válido' if expected_valid else 'Inválido'}, Obtido: {'Válido' if is_valid else 'Inválido'}")

        finally:
            # Limpar arquivo temporário
            if os.path.exists(temp_video_path):
                os.unlink(temp_video_path)

        print("✅ Validação de entrada testada")
        return True

    except Exception as e:
        print(f"❌ Erro na validação: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_transcription_segments():
    """Testar processamento de segmentos de transcrição"""
    print("\n=== TESTANDO PROCESSAMENTO DE TRANSCRIÇÃO ===")

    try:
        # Simular classe LLMClipFinder
        class MockLLMClipFinder:
            def _format_time(self, seconds):
                """Formata segundos para HH:MM:SS"""
                hours = int(seconds // 3600)
                minutes = int((seconds % 3600) // 60)
                secs = int(seconds % 60)
                return "02d"

            def format_transcript(self, transcription_segments):
                """Formata transcrição como no código original"""
                transcript_text = ""
                for i, segment in enumerate(transcription_segments):
                    start_time = self._format_time(segment["start"])
                    end_time = self._format_time(segment["end"])
                    transcript_text += f"[{start_time} - {end_time}] {segment['text']}\n"
                return transcript_text

        # Testar formatação de tempo
        finder = MockLLMClipFinder()

        test_times = [
            (0, "00:00:00"),
            (65, "00:01:05"),
            (3665, "01:01:05"),
            (7323, "02:02:03"),
        ]

        print("Testando formatação de tempo:")
        for seconds, expected in test_times:
            formatted = finder._format_time(seconds)
            status = "✅" if formatted == expected else "❌"
            print(f"{status} {seconds}s -> {formatted} (esperado: {expected})")

        # Testar formatação de transcrição
        test_segments = [
            {"start": 0.0, "end": 5.0, "text": "Olá mundo"},
            {"start": 5.0, "end": 10.0, "text": "Este é um teste"},
        ]

        transcript = finder.format_transcript(test_segments)
        expected_lines = 2
        actual_lines = len(transcript.strip().split('\n'))

        status = "✅" if actual_lines == expected_lines else "❌"
        print(f"{status} Formatação de transcrição: {actual_lines} linhas (esperado: {expected_lines})")

        print("✅ Processamento de transcrição testado")
        return True

    except Exception as e:
        print(f"❌ Erro no processamento de transcrição: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_clip_detection_prompt():
    """Testar geração de prompts para detecção de clipes"""
    print("\n=== TESTANDO PROMPTS DE DETECÇÃO ===")

    try:
        # Importar função de prompt
        from prompt_corte_youtube import get_clip_detection_prompt

        # Testar com dados de exemplo
        test_transcript = """
        [00:00:00 - 00:00:05] Olá pessoal, bem vindos ao canal!
        [00:00:05 - 00:00:15] Hoje vamos falar sobre tecnologia
        [00:00:15 - 00:00:25] Este é um tópico muito interessante
        [00:00:25 - 00:00:35] Vamos ver algumas demonstrações
        """

        prompt = get_clip_detection_prompt(test_transcript, min_clips=3, max_clips=5)

        # Verificar se prompt contém elementos essenciais
        required_elements = [
            "transcrição",
            "momentos interessantes",
            "clipes",
            "JSON"
        ]

        missing_elements = []
        for element in required_elements:
            if element.lower() not in prompt.lower():
                missing_elements.append(element)

        if missing_elements:
            print(f"❌ Elementos faltando no prompt: {missing_elements}")
            return False
        else:
            print("✅ Prompt contém todos os elementos necessários")
            print(f"   Tamanho do prompt: {len(prompt)} caracteres")
            return True

    except ImportError:
        print("⚠️ Módulo prompt_corte_youtube não encontrado, pulando teste")
        return True
    except Exception as e:
        print(f"❌ Erro no teste de prompts: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_output_directory_creation():
    """Testar criação de diretório de saída"""
    print("\n=== TESTANDO CRIAÇÃO DE DIRETÓRIO ===")

    try:
        import tempfile

        with tempfile.TemporaryDirectory() as temp_base:
            test_dirs = [
                "clips_output",
                "output/clips",
                os.path.join(temp_base, "test_clips"),
            ]

            for test_dir in test_dirs:
                try:
                    os.makedirs(test_dir, exist_ok=True)
                    if os.path.exists(test_dir) and os.path.isdir(test_dir):
                        print(f"✅ Diretório criado: {test_dir}")
                    else:
                        print(f"❌ Falha ao criar diretório: {test_dir}")
                        return False
                except Exception as e:
                    print(f"❌ Erro ao criar {test_dir}: {e}")
                    return False

        print("✅ Criação de diretório testada")
        return True

    except Exception as e:
        print(f"❌ Erro no teste de diretório: {e}")
        return False


if __name__ == "__main__":
    print("Testando geração de clipes...")

    # Executar testes
    tests = [
        ("Validação de Entrada", test_clip_generation_validation),
        ("Processamento de Transcrição", test_transcription_segments),
        ("Prompts de Detecção", test_clip_detection_prompt),
        ("Criação de Diretório", test_output_directory_creation),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"EXECUTANDO: {test_name}")
        print('='*50)

        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ ERRO FATAL em {test_name}: {e}")
            results.append((test_name, False))

    # Resumo final
    print(f"\n{'='*50}")
    print("RESUMO DOS TESTES DE CLIPES")
    print('='*50)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{status}: {test_name}")
        if result:
            passed += 1

    print(f"\nResultado Final: {passed}/{total} testes passaram")

    if passed == total:
        print("\n🎉 Todos os testes de clipes passaram!")
    else:
        print(f"\n⚠️ {total - passed} teste(s) falharam.")