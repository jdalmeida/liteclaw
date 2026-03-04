# Referência API

## LiteClawClient

Cliente para a API Gemini-compatible do lit serve.

### Construtor

```python
LiteClawClient(
    model="gemma3-1b",
    lit_path=None,
    port=9379,
    base_url=None,
    auto_start=True,
    backend="cpu",
)
```

### Métodos

| Método | Descrição |
|--------|-----------|
| `chat(message, history=None, max_tool_rounds=5)` | Chat com execução automática de tools. Retorna str. |
| `generate_content(contents, tools=None, tool_config=None)` | Chamada direta à API. Retorna dict. |
| `start_server()` | Inicia lit serve em background |
| `stop_server()` | Para o servidor |

### Atributos

- **tools** — `ToolRegistry` para registrar e chamar tools

---

## Agent

Loop de agente autônomo.

### Construtor

```python
Agent(
    client,
    session_manager=None,
    skills_loader=None,
    workspace_dir=None,
    config=None,
    max_tool_rounds=5,
    timeout_seconds=600,
)
```

### Métodos

| Método | Descrição |
|--------|-----------|
| `run(message, session_key="main", history=None, stream_callback=None)` | Executa um turno. Retorna str. |

---

## tool (decorator)

```python
@tool(name=None, description=None)
def minha_funcao(param: str) -> dict:
    ...
```

---

## ToolRegistry

| Método | Descrição |
|--------|-----------|
| `register(func)` | Registra função decorada com @tool |
| `register_function(name, func, description, parameters)` | Registro manual |
| `get_gemini_format()` | Retorna tools no formato Gemini |
| `call(name, arguments)` | Executa tool pelo nome |

---

## SkillsLoader

| Método | Descrição |
|--------|-----------|
| `load()` | Carrega skills elegíveis. Retorna `List[Skill]`. |
| `format_for_prompt(skills)` | Formata skills em XML para prompt |

---

## SessionManager

| Método | Descrição |
|--------|-----------|
| `get_messages(session_key, limit=None)` | Retorna histórico |
| `append_messages(session_key, messages, persist=True)` | Adiciona mensagens |
| `set_messages(session_key, messages, persist=True)` | Substitui histórico |
| `clear(session_key)` | Limpa sessão |
| `get_bootstrap_files()` | Retorna AGENTS.md, SOUL.md, TOOLS.md |

---

## Skill (dataclass)

- **name** — nome da skill
- **description** — descrição
- **instructions** — corpo em markdown
- **location** — caminho do diretório
- **metadata** — frontmatter parseado
