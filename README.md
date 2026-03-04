# LiteClaw

Agente autônomo com LLM local inspirado no [OpenClaw](https://github.com/openclaw/openclaw). Wrapper Python para o [LiteRT-LM](https://github.com/google-ai-edge/LiteRT-LM) da Google, com **tools**, **skills** (formato AgentSkills), Gateway WebSocket, WebChat e canais (Telegram, Discord).

## Características

- **LLM local** — Executa modelos via `lit serve` (LiteRT-LM), sem dependência de APIs externas
- **Tools** — Function calling com decorator `@tool` e tools builtin (exec, read, write, web_fetch)
- **Skills** — Formato AgentSkills (SKILL.md) com gating e injeção no prompt
- **Gateway** — Servidor WebSocket + HTTP na porta 18789
- **WebChat** — Interface web para conversar com o agente
- **Canais** — Telegram e Discord como canais de mensagem

## Instalação

```bash
# Linux/macOS
./scripts/install.sh

# Windows (PowerShell)
.\scripts\install.ps1
```

Ou manualmente: `python -m venv .venv` → `source .venv/bin/activate` → `pip install -e .`

**Requisitos:** Python 3.8+, executável `lit` do LiteRT-LM no projeto.

## Início rápido

```bash
# 1. Inicie o gateway (WebChat em http://127.0.0.1:18789)
liteclaw gateway --verbose

# 2. Envie uma mensagem via CLI
liteclaw agent -m "Olá! O que você consegue fazer?"
```

Ou use em Python:

```python
from liteclaw import LiteClawClient, tool

@tool(description="Retorna o clima de uma localização")
def get_weather(location: str) -> dict:
    return {"location": location, "temperature": 25, "condition": "Sunny"}

client = LiteClawClient(model="qwen2.5-1.5b", auto_start=True)
client.tools.register(get_weather)
print(client.chat("Como está o clima em Paris?"))
```

## Documentação

| Documento | Descrição |
|-----------|-----------|
| [Instalação](docs/instalacao.md) | Requisitos e instalação detalhada |
| [Guia rápido](docs/guia-rapido.md) | Primeiros passos e exemplos |
| [Arquitetura](docs/arquitetura.md) | Visão geral do sistema |
| [Tools](docs/tools.md) | Como criar e usar tools |
| [Skills](docs/skills.md) | Formato AgentSkills e gating |
| [Gateway](docs/gateway.md) | Protocolo WebSocket e API |
| [Canais](docs/canais.md) | Telegram, Discord e configuração |
| [Configuração](docs/configuracao.md) | config.json e variáveis de ambiente |
| [Referência API](docs/api.md) | Classes e métodos |

## Estrutura do projeto

```
liteclaw/
├── client.py       # LiteClawClient (lit serve)
├── agent.py        # Loop do agente
├── session.py      # Gerenciador de sessões
├── skills.py       # Loader de skills
├── tools.py        # @tool e ToolRegistry
├── tools_builtin.py# exec, read, write, web_fetch
├── gateway/        # Servidor HTTP + WebSocket
├── channels/       # Telegram, Discord
└── web/            # WebChat (HTML/JS)
```

## Modelos recomendados

Para **function calling**, use modelos treinados para tools:

- **FunctionGemma-270M** (TinyGarden): `lit pull google/functiongemma-270m-it`
- Consulte a [documentação do LiteRT-LM](https://github.com/google-ai-edge/LiteRT-LM)

## Licença

Apache-2.0 (compatível com LiteRT-LM)
