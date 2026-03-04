# Arquitetura

## Visão geral

O LiteClaw é composto por camadas que orquestram o LLM local, tools, skills e canais de mensagem.

```
┌─────────────────────────────────────────────────────────────┐
│                      Canais (entrada)                        │
│  WebChat │ Telegram │ Discord │ CLI                          │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│                    Gateway (HTTP + WebSocket)                │
│  Porta 18789 │ RPC: connect, agent, agent.wait, health      │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│                      Agent Loop                             │
│  Session Manager │ Skills Loader │ Tool Registry             │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│                   LiteClawClient                             │
│  lit serve (porta 9379) │ API Gemini-compatible             │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│                    LiteRT-LM (lit)                           │
│  Modelo local │ Function calling                            │
└─────────────────────────────────────────────────────────────┘
```

## Componentes

### LiteClawClient

Gerencia o servidor `lit serve` e envia requisições para a API Gemini-compatible. Responsável por:

- Iniciar/parar o servidor
- Chamar `generateContent` com contents e tools
- Converter respostas do modelo

### Agent

Loop de agente autônomo:

1. **Intake** — recebe mensagem e carrega histórico da sessão
2. **Context** — monta system prompt com bootstrap (AGENTS.md, SOUL.md) e skills
3. **Model** — chama o LLM com contents e tools
4. **Tools** — executa function calls retornadas pelo modelo
5. **Stream** — emite eventos (assistant, tool, lifecycle)
6. **Persist** — salva histórico na sessão

### SessionManager

Persiste mensagens por `sessionKey` em `~/.liteclaw/sessions/`. Cada sessão mantém o histórico da conversa para contexto.

### SkillsLoader

Carrega skills no formato AgentSkills de:

- `./skills` (workspace)
- `~/.liteclaw/skills` (managed)
- `liteclaw/bundled_skills` (bundled)

Aplica gating (`requires.bins`, `requires.env`, `requires.config`) e injeta a lista no system prompt.

### Gateway

Servidor aiohttp que:

- Serve WebChat em `GET /`
- Expõe WebSocket em `GET /ws`
- Despacha RPC: connect, agent, agent.wait, health, send
- Inicia canais (Telegram, Discord) conforme config

### Canais

Cada canal implementa a interface `Channel`: connect, disconnect, send, on_message. Ao receber mensagem, chama o agent e envia a resposta de volta.

## Fluxo de uma mensagem

1. Usuário envia mensagem (WebChat, Telegram, Discord ou CLI)
2. Gateway recebe e enfileira por session_key (serialização)
3. Agent carrega sessão, skills e monta o prompt
4. LiteClawClient chama lit serve
5. Modelo retorna texto e/ou tool calls
6. Tools são executadas e resultados enviados de volta ao modelo
7. Resposta final é persistida e enviada ao canal
