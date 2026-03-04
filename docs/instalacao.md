# Instalação

## Requisitos

- **Python** 3.8 ou superior
- **LiteRT-LM** — executável `lit` no diretório do projeto ou no PATH
- **Modelo** — compatível com tool calling (ex: FunctionGemma/TinyGarden) para function calling; modelos genéricos para chat simples

## Instalação do LiteClaw

### Script único (recomendado)

```bash
# Linux/macOS
cd liteclaw && ./scripts/install.sh

# Windows (PowerShell)
cd liteclaw; .\scripts\install.ps1
```

### Instalação manual

```bash
# Clone o repositório (se aplicável)
git clone https://github.com/seu-usuario/liteclaw.git
cd liteclaw

# Crie e ative o ambiente virtual
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows

# Instale o pacote
pip install -e .
```

## Instalação do LiteRT-LM

O LiteClaw depende do executável `lit` do [LiteRT-LM](https://github.com/google-ai-edge/LiteRT-LM). Siga a documentação oficial para instalação.

Resumo típico:

```bash
# Baixe o lit (consulte o repositório LiteRT-LM)
# Coloque o executável em ./lit no diretório do projeto
# ou configure lit_path ao criar o LiteClawClient
```

## Baixando modelos

```bash
# Modelo com suporte a tools (FunctionGemma)
lit pull google/functiongemma-270m-it

# Modelos genéricos (chat sem tools)
lit pull google/gemma3-1b-it
lit pull qwen2.5-1.5b
```

## Dependências opcionais

- **PyYAML** — parsing de frontmatter em skills (recomendado)
- **python-telegram-bot** — canal Telegram
- **discord.py** — canal Discord

Todas são instaladas por padrão com `pip install -e .`.

## Verificação

```bash
# Verifique a instalação
liteclaw gateway --help
liteclaw agent --help
```

```python
# Em Python
from liteclaw import LiteClawClient, Agent
print("OK")
```
