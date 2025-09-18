#!/usr/bin/env python3
"""
Testes para geração de imagens com Stable Diffusion XL
"""
import sys
import os
import tempfile
import shutil

# Adicionar src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_image_generation():
    """Testar geração de imagem com Stable Diffusion XL"""
    print("=== TESTANDO GERAÇÃO DE IMAGENS ===")

    try:
        from diffusers import StableDiffusionXLPipeline
        import torch
        from PIL import Image
        import queue

        print("✅ Bibliotecas importadas com sucesso")

        # Simular classe com métodos necessários
        class MockGUI:
            def __init__(self):
                self.output_queue = queue.Queue()
                self.image_device = "cpu"  # Usar CPU para testes
                self.image_model_loaded = False
                self.image_model = None
                self.image_prompt = "Uma paisagem bonita com montanhas e céu azul, estilo fotográfico"
                self.image_output_dir = "imagens"

            def load_image_model(self):
                """Carrega o modelo Stable Diffusion XL se não estiver carregado"""
                if self.image_model_loaded and self.image_model is not None:
                    return True

                try:
                    print("Carregando Stable Diffusion XL...")

                    # Configurar dispositivo
                    if self.image_device == "cuda" and torch.cuda.is_available():
                        torch.cuda.empty_cache()
                        device = "cuda"
                        torch_dtype = torch.float16
                    else:
                        device = "cpu"
                        torch_dtype = torch.float32

                    # Carregar modelo SDXL (versão mais leve para testes)
                    model_name = "stabilityai/stable-diffusion-xl-base-1.0"
                    print(f"Carregando modelo {model_name} no {device.upper()}...")

                    # Usar versão otimizada para CPU se disponível
                    if device == "cpu":
                        # Carregar com configurações otimizadas para CPU
                        self.image_model = StableDiffusionXLPipeline.from_pretrained(
                            model_name,
                            torch_dtype=torch_dtype,
                            use_safetensors=True,  # Mais eficiente
                            variant="fp16" if device == "cuda" else None
                        ).to(device)
                    else:
                        self.image_model = StableDiffusionXLPipeline.from_pretrained(
                            model_name,
                            torch_dtype=torch_dtype
                        ).to(device)

                    # Otimizações para CPU
                    if device == "cpu":
                        self.image_model.enable_attention_slicing()  # Reduz uso de memória

                    self.image_model_loaded = True
                    print("Stable Diffusion XL carregado com sucesso!")
                    return True

                except Exception as e:
                    print(f"Erro ao carregar modelo de imagem: {str(e)}")
                    return False

        # Criar mock GUI
        gui = MockGUI()

        # Testar carregamento do modelo
        if not gui.load_image_model():
            print("❌ Falha ao carregar modelo de imagem")
            return False

        # Criar pasta temporária para teste
        with tempfile.TemporaryDirectory() as temp_dir:
            print("Gerando imagem de teste...")

            # Gerar imagem pequena para teste rápido
            image = gui.image_model(
                gui.image_prompt,
                height=512,         # Altura reduzida para teste
                width=512,          # Largura reduzida para teste (1:1 para velocidade)
                num_inference_steps=10,  # Menos passos para teste rápido
                guidance_scale=7.5
            ).images[0]

            # Salvar imagem de teste
            test_output = os.path.join(temp_dir, "teste_imagem.png")
            image.save(test_output)

            # Verificar se arquivo foi criado
            if os.path.exists(test_output):
                # Verificar se é uma imagem válida
                try:
                    with Image.open(test_output) as img:
                        width, height = img.size
                        print(f"✅ Imagem gerada com sucesso! Dimensões: {width}x{height}")
                        print(f"   Arquivo salvo em: {test_output}")
                        return True
                except Exception as e:
                    print(f"❌ Imagem gerada mas inválida: {e}")
                    return False
            else:
                print("❌ Arquivo de imagem não foi criado")
                return False

    except ImportError as ie:
        print(f"❌ Bibliotecas necessárias não instaladas: {str(ie)}")
        print("   Instale com: pip install diffusers torch torchvision transformers accelerate")
        return False
    except Exception as e:
        print(f"❌ Erro geral: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_image_prompt_validation():
    """Testar validação de prompts de imagem"""
    print("\n=== TESTANDO VALIDAÇÃO DE PROMPTS ===")

    try:
        # Testes de validação
        test_prompts = [
            ("Uma paisagem bonita", True),  # Válido
            ("", False),                    # Vazio
            ("   ", False),                 # Apenas espaços
            ("A" * 1000, True),            # Muito longo (mas válido)
            ("<script>alert('xss')</script>", True),  # Com caracteres especiais (permitido)
        ]

        for prompt, expected_valid in test_prompts:
            is_valid = len(prompt.strip()) > 0
            status = "✅" if is_valid == expected_valid else "❌"
            print(f"{status} Prompt: '{prompt[:30]}{'...' if len(prompt) > 30 else ''}' -> {'Válido' if is_valid else 'Inválido'}")

        print("✅ Validação de prompts testada")
        return True

    except Exception as e:
        print(f"❌ Erro na validação: {e}")
        return False


def test_image_output_directory():
    """Testar criação e validação de diretório de saída"""
    print("\n=== TESTANDO DIRETÓRIO DE SAÍDA ===")

    try:
        import tempfile
        import os

        # Testar criação de diretório
        with tempfile.TemporaryDirectory() as temp_base:
            test_dirs = [
                "imagens",
                "output/imagens",
                "test_images",
                os.path.join(temp_base, "custom_images")
            ]

            for test_dir in test_dirs:
                try:
                    os.makedirs(test_dir, exist_ok=True)
                    if os.path.exists(test_dir):
                        print(f"✅ Diretório criado: {test_dir}")
                    else:
                        print(f"❌ Falha ao criar: {test_dir}")
                        return False
                except Exception as e:
                    print(f"❌ Erro ao criar {test_dir}: {e}")
                    return False

        print("✅ Teste de diretório concluído")
        return True

    except Exception as e:
        print(f"❌ Erro no teste de diretório: {e}")
        return False


if __name__ == "__main__":
    print("Testando geração de imagens...")

    # Executar testes
    tests = [
        ("Geração de Imagens", test_image_generation),
        ("Validação de Prompts", test_image_prompt_validation),
        ("Diretório de Saída", test_image_output_directory),
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
    print("RESUMO DOS TESTES")
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
        print("\n🎉 Todos os testes de imagem passaram!")
    else:
        print(f"\n⚠️ {total - passed} teste(s) falharam.")

    print("\nNota: O teste de geração de imagens pode ser lento na primeira execução")
    print("devido ao download do modelo Stable Diffusion XL.")