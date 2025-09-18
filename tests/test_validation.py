#!/usr/bin/env python3
"""
Testes para validação de entrada e configurações
"""
import sys
import os
import json
import tempfile

# Adicionar src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_config_file_operations():
    """Testar operações com arquivo de configuração"""
    print("=== TESTANDO OPERAÇÕES DE CONFIGURAÇÃO ===")

    try:
        # Simular classe de configuração como na GUI
        class MockConfig:
            def __init__(self):
                self.config_file = None
                self.saved_api_key = ""
                self.saved_theme = "dark"
                self.saved_font_size = 12

            def load_config(self, config_path):
                """Carregar configurações do arquivo"""
                self.config_file = config_path
                self.saved_api_key = ""
                try:
                    if os.path.exists(config_path):
                        with open(config_path, 'r', encoding='utf-8') as f:
                            config = json.load(f)
                            self.saved_api_key = config.get('api_key', '')
                            self.saved_theme = config.get('theme', 'dark')
                            self.saved_font_size = config.get('font_size', 12)
                        return True
                    else:
                        # Arquivo não existe, usar padrões
                        return True
                except json.JSONDecodeError:
                    print(f"Arquivo de configuração corrompido: {config_path}")
                    return False
                except Exception as e:
                    print(f"Erro ao carregar configurações: {e}")
                    return False

            def save_config(self, config_path, api_key="", theme="dark", font_size=12):
                """Salvar configurações no arquivo"""
                self.config_file = config_path
                try:
                    config = {
                        'api_key': api_key,
                        'theme': theme,
                        'font_size': font_size
                    }
                    with open(config_path, 'w', encoding='utf-8') as f:
                        json.dump(config, f, indent=2, ensure_ascii=False)
                    return True
                except Exception as e:
                    print(f"Erro ao salvar configurações: {e}")
                    return False

        config = MockConfig()

        # Testar com arquivo temporário
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            temp_config_path = temp_file.name

        try:
            # Teste 1: Salvar configuração
            test_api_key = "test_key_123"
            test_theme = "light"
            test_font_size = 14

            success = config.save_config(temp_config_path, test_api_key, test_theme, test_font_size)
            if success:
                print("✅ Configuração salva com sucesso")
            else:
                print("❌ Falha ao salvar configuração")
                return False

            # Teste 2: Carregar configuração
            load_success = config.load_config(temp_config_path)
            if load_success:
                print("✅ Configuração carregada com sucesso")
            else:
                print("❌ Falha ao carregar configuração")
                return False

            # Teste 3: Verificar valores
            checks = [
                ("API Key", config.saved_api_key, test_api_key),
                ("Theme", config.saved_theme, test_theme),
                ("Font Size", config.saved_font_size, test_font_size),
            ]

            for name, actual, expected in checks:
                if actual == expected:
                    print(f"✅ {name}: {actual}")
                else:
                    print(f"❌ {name}: esperado '{expected}', obtido '{actual}'")
                    return False

            # Teste 4: Arquivo corrompido
            with open(temp_config_path, 'w') as f:
                f.write("invalid json content")

            corrupted_load = config.load_config(temp_config_path)
            if not corrupted_load:
                print("✅ Detecção de arquivo corrompido funciona")
            else:
                print("❌ Não detectou arquivo corrompido")
                return False

        finally:
            # Limpar arquivo temporário
            if os.path.exists(temp_config_path):
                os.unlink(temp_config_path)

        print("✅ Operações de configuração testadas")
        return True

    except Exception as e:
        print(f"❌ Erro nas operações de configuração: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_url_validation():
    """Testar validação de URLs do YouTube"""
    print("\n=== TESTANDO VALIDAÇÃO DE URLs ===")

    try:
        # Simular função de validação como na GUI
        def is_valid_youtube_url(url):
            """Validar se a URL é válida do YouTube"""
            try:
                import urllib.parse
                parsed_url = urllib.parse.urlparse(url.strip())
                valid_domains = ['www.youtube.com', 'youtube.com', 'youtu.be', 'm.youtube.com']

                if parsed_url.netloc in valid_domains:
                    return True

                # Verificar youtu.be short links
                if parsed_url.netloc == 'youtu.be' and parsed_url.path and len(parsed_url.path) > 1:
                    return True

                return False
            except:
                return False

        # Casos de teste
        test_urls = [
            # (url, expected_valid)
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", True),
            ("https://youtube.com/watch?v=dQw4w9WgXcQ", True),
            ("https://youtu.be/dQw4w9WgXcQ", True),
            ("https://m.youtube.com/watch?v=dQw4w9WgXcQ", True),
            ("https://www.youtube.com/playlist?list=PLrAXtmRdnEQy4qtr5GrLOg", True),
            ("", False),
            ("not_a_url", False),
            ("https://google.com", False),
            ("https://youtube.com.br/watch?v=test", False),  # domínio brasileiro
            ("https://youtu.be/", False),  # youtu.be sem ID
            ("https://www.youtube.com/", True),  # URL base válida
        ]

        all_passed = True
        for url, expected_valid in test_urls:
            is_valid = is_valid_youtube_url(url)
            status = "✅" if is_valid == expected_valid else "❌"
            result_text = "Válida" if is_valid else "Inválida"

            print(f"{status} '{url}' -> {result_text}")

            if is_valid != expected_valid:
                print(f"   Esperado: {'Válida' if expected_valid else 'Inválida'}")
                all_passed = False

        if all_passed:
            print("✅ Validação de URLs testada com sucesso")
            return True
        else:
            print("❌ Alguns testes de URL falharam")
            return False

    except Exception as e:
        print(f"❌ Erro na validação de URLs: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_filename_normalization():
    """Testar normalização de nomes de arquivo"""
    print("\n=== TESTANDO NORMALIZAÇÃO DE ARQUIVOS ===")

    try:
        # Simular função de normalização como no código
        def normalize_filename(filename):
            """Remove acentos e substitui espaços por underscores no nome do arquivo"""
            import unicodedata
            import re

            # Remove acentos
            normalized = unicodedata.normalize('NFD', filename)
            ascii_filename = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')

            # Substitui espaços por underscores
            ascii_filename = ascii_filename.replace(' ', '_')

            # Remove caracteres especiais exceto pontos, hífens e underscores
            ascii_filename = re.sub(r'[^\w\-_\.]', '', ascii_filename)

            return ascii_filename

        # Casos de teste
        test_files = [
            # (input, expected_output)
            ("teste vídeo.mp4", "teste_video.mp4"),
            ("vídeo com ácentos.mp4", "video_com_acentos.mp4"),
            ("file with spaces.mp4", "file_with_spaces.mp4"),
            ("special-chars!@#$%.mp4", "special-chars.mp4"),
            ("normal_file.mp4", "normal_file.mp4"),
            ("", ""),
            ("a" * 100 + ".mp4", "a" * 100 + ".mp4"),  # nome muito longo
        ]

        all_passed = True
        for input_name, expected in test_files:
            normalized = normalize_filename(input_name)
            status = "✅" if normalized == expected else "❌"

            print(f"{status} '{input_name}' -> '{normalized}'")

            if normalized != expected:
                print(f"   Esperado: '{expected}'")
                all_passed = False

        if all_passed:
            print("✅ Normalização de arquivos testada com sucesso")
            return True
        else:
            print("❌ Alguns testes de normalização falharam")
            return False

    except Exception as e:
        print(f"❌ Erro na normalização de arquivos: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_directory_operations():
    """Testar operações com diretórios"""
    print("\n=== TESTANDO OPERAÇÕES COM DIRETÓRIOS ===")

    try:
        import tempfile

        with tempfile.TemporaryDirectory() as temp_base:
            # Testar criação de múltiplos diretórios
            test_dirs = [
                "temp",
                "downloads",
                "output/clips",
                "output/tts",
                "output/images",
                os.path.join(temp_base, "nested", "deep", "path"),
            ]

            for test_dir in test_dirs:
                try:
                    os.makedirs(test_dir, exist_ok=True)

                    if os.path.exists(test_dir) and os.path.isdir(test_dir):
                        print(f"✅ Diretório criado: {test_dir}")

                        # Testar permissões de escrita
                        test_file = os.path.join(test_dir, "test_write.txt")
                        try:
                            with open(test_file, 'w') as f:
                                f.write("test")
                            os.unlink(test_file)
                            print(f"   ✅ Permissões de escrita OK")
                        except Exception as e:
                            print(f"   ❌ Erro de permissões: {e}")
                            return False

                    else:
                        print(f"❌ Falha ao criar diretório: {test_dir}")
                        return False

                except Exception as e:
                    print(f"❌ Erro ao criar {test_dir}: {e}")
                    return False

        print("✅ Operações com diretórios testadas")
        return True

    except Exception as e:
        print(f"❌ Erro nas operações com diretórios: {e}")
        return False


def test_json_operations():
    """Testar operações com JSON (como usado nas configurações)"""
    print("\n=== TESTANDO OPERAÇÕES JSON ===")

    try:
        import json

        # Testar dados de configuração típicos
        test_configs = [
            {
                "api_key": "gemini_key_123",
                "theme": "dark",
                "font_size": 12,
                "language": "pt-BR"
            },
            {
                "api_key": "",
                "theme": "light",
                "font_size": 14
            },
            {
                "empty_config": True
            }
        ]

        for i, config in enumerate(test_configs):
            try:
                # Serializar
                json_str = json.dumps(config, indent=2, ensure_ascii=False)

                # Desserializar
                parsed_config = json.loads(json_str)

                # Verificar se são iguais
                if config == parsed_config:
                    print(f"✅ Configuração {i+1}: serialização/desserialização OK")
                else:
                    print(f"❌ Configuração {i+1}: dados corrompidos na serialização")
                    return False

            except Exception as e:
                print(f"❌ Erro na configuração {i+1}: {e}")
                return False

        # Testar JSON malformado
        malformed_jsons = [
            "{invalid json",
            '{"missing": "comma" "invalid": "format"}',
            '["incomplete array"',
            '{"unclosed": "object"',
        ]

        for malformed in malformed_jsons:
            try:
                json.loads(malformed)
                print(f"❌ JSON malformado não detectado: {malformed[:30]}...")
                return False
            except json.JSONDecodeError:
                print(f"✅ JSON malformado corretamente rejeitado")
            except Exception as e:
                print(f"❌ Erro inesperado com JSON malformado: {e}")
                return False

        print("✅ Operações JSON testadas")
        return True

    except Exception as e:
        print(f"❌ Erro nas operações JSON: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Testando validação e configurações...")

    # Executar testes
    tests = [
        ("Operações de Configuração", test_config_file_operations),
        ("Validação de URLs", test_url_validation),
        ("Normalização de Arquivos", test_filename_normalization),
        ("Operações com Diretórios", test_directory_operations),
        ("Operações JSON", test_json_operations),
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
    print("RESUMO DOS TESTES DE VALIDAÇÃO")
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
        print("\n🎉 Todos os testes de validação passaram!")
    else:
        print(f"\n⚠️ {total - passed} teste(s) falharam.")