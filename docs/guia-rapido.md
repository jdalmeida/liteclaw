# Guia rápido

## 1. Chat simples (Python)

```python
from liteclaw import LiteClawClient

client = LiteClawClient(model="qwen2.5-1.5b", auto_start=True)
response = client.chat("Qual a capital do Brasil?")
print(response)
```

## 2. Chat com tools

```python
from liteclaw import LiteClawClient, tool

@tool(description="Retorna o clima de uma localização")
def get_weather(location: str) -> dict:
    return {"location": location, "temperature": 25, "condition": "Sunny"}

client = LiteClawClient(model="qwen2.5-1.5b", auto_start=True)
client.tools.register(get_weather)

print(client.chat("Como está o clima em São Paulo?"))
```

## 3. Agent com skills e tools builtin

```python
from liteclaw import Agent, LiteClawClient
from liteclaw.session import SessionManager
from liteclaw.skills import SkillsLoader
from liteclaw.tools_builtin import register_builtin_tools

client = LiteClawClient(model="qwen2.5-1.5b", auto_start=True)
register_builtin_tools(client.tools)

agent = Agent(
    client=client,
    session_manager=SessionManager(),
    skills_loader=SkillsLoader(),
)

print(agent.run("Liste os arquivos do diretório atual"))
```

## 4. Gateway e WebChat

```bash
# Terminal 1: inicie o gateway
liteclaw gateway --verbose

# Terminal 2: envie mensagem via CLI
liteclaw agent -m "Olá!"
```

Acesse **http://127.0.0.1:18789** no navegador para o WebChat.

## 5. Exemplos no repositório

```bash
# Chat interativo com tools
python examples/chat_with_tools.py

# Agent com skills e tools builtin
python examples/agent_with_skills.py
```
