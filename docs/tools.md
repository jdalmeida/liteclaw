# Tools

Tools são funções que o modelo pode invocar durante a conversa (function calling).

## Decorator @tool

```python
from liteclaw import tool

@tool(description="Retorna o clima de uma localização")
def get_weather(location: str) -> dict:
    return {"location": location, "temperature": 25, "condition": "Sunny"}
```

Parâmetros do decorator:

- **name** — nome da tool (default: nome da função)
- **description** — descrição para o modelo (default: primeira linha da docstring)

## Registro

```python
from liteclaw import LiteClawClient, tool

client = LiteClawClient(auto_start=True)
client.tools.register(get_weather)
```

## Registro manual

```python
client.tools.register_function(
    name="minha_tool",
    func=minha_funcao,
    description="Descrição",
    parameters={
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "..."},
        },
        "required": ["param1"],
    },
)
```

## Tools builtin

O LiteClaw inclui tools inspiradas no OpenClaw:

| Tool | Descrição |
|------|-----------|
| `read` | Lê conteúdo de arquivo no workspace |
| `write` | Escreve conteúdo em arquivo |
| `edit` | Retorna conteúdo para edição (usa `write` para aplicar) |
| `exec` | Executa comando no shell (cwd = workspace) |
| `bash` | Alias para `exec` |
| `web_fetch` | Busca conteúdo de URL |
| `web_search` | Busca na web (Brave API, requer `BRAVE_API_KEY`) |

Para registrar todas:

```python
from liteclaw.tools_builtin import register_builtin_tools

register_builtin_tools(client.tools)
```

## Workspace

As tools `read`, `write`, `edit`, `exec` e `bash` usam o workspace como diretório base. Padrão: `~/.liteclaw/workspace`. Configure com `LITECLAW_WORKSPACE` ou parâmetro `workspace`.

## Grupos de tools

Para perfis (ex: coding, minimal):

```python
from liteclaw.tools_builtin import TOOL_GROUPS

# TOOL_GROUPS = {
#     "group:fs": ["read", "write", "edit"],
#     "group:runtime": ["exec", "bash"],
#     "group:web": ["web_fetch", "web_search"],
# }
```
