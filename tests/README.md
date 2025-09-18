# Testes do AutoCutter-AI

Esta pasta contém testes automatizados para validar as funcionalidades do AutoCutter-AI.

## Estrutura dos Testes

- `test_tts.py` - Testes para geração de áudio TTS (Text-to-Speech)
- `test_images.py` - Testes para geração de imagens com Stable Diffusion XL
- `test_clips.py` - Testes para geração de clipes de vídeo
- `test_validation.py` - Testes para validação de entrada e configurações

## Como Executar os Testes

### Executar Todos os Testes

```bash
# Na raiz do projeto
python -m pytest tests/ -v
```

Ou executar individualmente:

```bash
python tests/test_tts.py
python tests/test_images.py
python tests/test_clips.py
python tests/test_validation.py
```

## Dependências dos Testes

### Para todos os testes:
- Python 3.8+
- Bibliotecas básicas (os, sys, json, tempfile)

### Para teste de TTS (`test_tts.py`):
```bash
pip install TTS pydub torch
```

### Para teste de imagens (`test_images.py`):
```bash
pip install diffusers torch transformers accelerate
```

### Para teste de clipes (`test_clips.py`):
- Requer o arquivo `prompt_corte_youtube.py` no diretório raiz
- Para testes completos: `pip install whisper google-generativeai`

### Para teste de validação (`test_validation.py`):
- Apenas bibliotecas padrão do Python

## Tipos de Teste

### 1. Testes Unitários
- Validação de entrada
- Formatação de dados
- Operações básicas

### 2. Testes de Integração
- Carregamento de modelos de IA
- Geração de conteúdo
- Operações com arquivos

### 3. Testes de Funcionalidade
- Fluxos completos de geração
- Validação end-to-end

## Notas Importantes

### ⚠️ Testes de IA Pesados
Os testes de geração de imagens e TTS fazem download de modelos grandes na primeira execução:
- **Stable Diffusion XL**: ~6.5GB
- **XTTS v2**: ~1.8GB

### 🖥️ Requisitos de Hardware
- **CPU**: Pelo menos 8GB RAM para testes básicos
- **GPU**: Recomendado para testes de IA (CUDA)
- **Armazenamento**: ~10GB livres para modelos

### 🔧 Configuração
Alguns testes podem ser lentos dependendo do hardware. Os testes foram otimizados para:
- Usar configurações reduzidas quando possível
- Fallback para CPU se GPU não disponível
- Timeout apropriados para evitar travamentos

## Resultados Esperados

### ✅ Testes que Devem Passar
- Validação de entrada
- Operações com arquivos/diretórios
- Formatação de dados
- Configurações JSON

### ⚠️ Testes que Podem Falhar
- Geração de imagens/TTS sem dependências instaladas
- Testes de rede (URLs do YouTube)
- Operações que requerem GPU

## Debugging

Se um teste falhar:

1. **Verifique as dependências**:
   ```bash
   pip list | grep -E "(torch|TTS|diffusers|whisper)"
   ```

2. **Execute com debug**:
   ```bash
   python tests/test_X.py 2>&1 | tee debug.log
   ```

3. **Teste componentes individuais**:
   - Importe bibliotecas manualmente
   - Teste operações básicas primeiro

## Contribuição

Para adicionar novos testes:

1. Siga o padrão dos testes existentes
2. Use `tempfile` para arquivos temporários
3. Inclua tratamento de exceções adequado
4. Documente dependências especiais
5. Adicione ao README se necessário