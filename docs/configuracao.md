# Configuração

## Arquivo de configuração

O LiteClaw lê `~/.liteclaw/config.json` ao iniciar o Gateway.

Exemplo completo:

```json
{
  "channels": {
    "telegram": {
      "botToken": "123456:ABC...",
      "allowFrom": ["*"]
    },
    "discord": {
      "token": "MTIzNDU2...",
      "allowFrom": ["*"]
    }
  },
  "skills": {
    "entries": {
      "minha-skill": {
        "enabled": true
      }
    },
    "load": {
      "extraDirs": ["/caminho/para/skills"]
    }
  }
}
```

## Variáveis de ambiente

| Variável | Descrição |
|----------|-----------|
| `LITECLAW_WORKSPACE` | Diretório do workspace (default: `~/.liteclaw/workspace`) |
| `BRAVE_API_KEY` | Chave para web_search (Brave Search API) |

## Diretórios padrão

| Caminho | Descrição |
|---------|-----------|
| `~/.liteclaw/workspace` | Workspace (AGENTS.md, SOUL.md, TOOLS.md) |
| `~/.liteclaw/sessions` | Persistência de sessões |
| `~/.liteclaw/skills` | Skills managed |
| `~/.liteclaw/config.json` | Configuração |

## Bootstrap (workspace)

Arquivos opcionais em `~/.liteclaw/workspace/` injetados no system prompt:

- **AGENTS.md** — instruções gerais do agente
- **SOUL.md** — personalidade/comportamento
- **TOOLS.md** — orientações sobre uso de tools
