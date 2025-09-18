# Compilação AutoCutter-AI

Este diretório contém scripts para compilar o AutoCutter-AI em um executável standalone.

## Arquivos

- `AutoCutter-AI.spec` - Configuração do PyInstaller
- `compiler.bat` - Script principal de compilação
- `test_build.bat` - Script para testar o executável compilado

## Como Compilar

### Pré-requisitos

1. **Python 3.8+** instalado e no PATH
2. **Git** (opcional, para clonar o repositório)
3. Pelo menos **8GB RAM** livre
4. **50GB espaço em disco** (para dependências e build)

### Passo 1: Instalar Dependências

```bash
pip install -r requirements.txt
pip install pyinstaller
```

### Passo 2: Executar Compilação

```bash
# Execute o compilador
compiler.bat
```

O processo pode levar **30-60 minutos** dependendo do hardware, especialmente no primeiro build.

### Passo 3: Testar Executável

```bash
# Testar o executável compilado
test_build.bat
```

## Estrutura do Build

```
dist/
└── AutoCutter-AI.exe    # Executável principal
```

## Configuração do PyInstaller

### Incluído no Build
- ✅ Todas as bibliotecas Python necessárias
- ✅ Interface PyQt5 completa
- ✅ Modelos de IA (baixados em runtime)
- ✅ Arquivos de configuração
- ✅ Scripts auxiliares

### Excluído do Build
- ❌ Bibliotecas desnecessárias (tkinter, matplotlib)
- ❌ Arquivos de desenvolvimento
- ❌ Cache e arquivos temporários

## Solução de Problemas

### Erro: "PyInstaller não encontrado"
```bash
pip install --upgrade pyinstaller
```

### Erro: "Dependência faltando"
```bash
pip install -r requirements.txt --force-reinstall
```

### Erro: "Sem memória"
- Feche outros programas
- Reinicie o computador
- Use um ambiente virtual limpo

### Erro: "Arquivo muito grande"
- O executável pode ter 500MB-2GB
- Considere usar `--onedir` ao invés de `--onefile` se disponível

## Distribuição

### Para Usuários Finais
1. Copie apenas o `AutoCutter-AI.exe`
2. Certifique-se de que tenham Python instalado
3. Os modelos de IA serão baixados automaticamente

### Requisitos do Sistema
- Windows 10/11
- Python 3.8+ (incluído no build)
- 8GB RAM mínimo
- GPU NVIDIA recomendada para IA

## Otimizações

### Reduzir Tamanho
- Usar UPX compression (já habilitado)
- Excluir bibliotecas não utilizadas
- Usar `--exclude-module`

### Melhorar Performance
- Compilar com `--optimize 1` ou `--optimize 2`
- Usar `--strip` para remover debug info
- Considerar `--win-private-assemblies`

## Comandos Avançados

### Build personalizado
```bash
pyinstaller --onefile --windowed --name AutoCutter-AI src/gui/gui.py
```

### Debug do build
```bash
pyinstaller --debug=all AutoCutter-AI.spec
```

### Limpar build anterior
```bash
rmdir /s /q build dist
pyinstaller --clean AutoCutter-AI.spec
```