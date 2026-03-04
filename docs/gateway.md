# Gateway

O Gateway é o servidor HTTP + WebSocket que expõe o agente. Porta padrão: **18789**.

## Endpoints

| Rota | Descrição |
|------|-----------|
| `GET /` | WebChat (interface web) |
| `GET /app.js` | JavaScript do WebChat |
| `GET /ws` | WebSocket (protocolo RPC) |

## Protocolo WebSocket

### Conexão

Primeiro frame obrigatório: **connect**

```json
{
  "type": "req",
  "id": "1",
  "method": "connect",
  "params": {
    "role": "client",
    "deviceId": "meu-dispositivo"
  }
}
```

Resposta:

```json
{
  "type": "res",
  "id": "1",
  "ok": true,
  "payload": {
    "status": "ok",
    "snapshot": {
      "presence": {},
      "health": {"status": "ok", "litServe": "ok"}
    }
  }
}
```

### Métodos RPC

#### agent

Inicia um run do agente.

```json
{
  "type": "req",
  "id": "2",
  "method": "agent",
  "params": {
    "message": "Olá!",
    "sessionKey": "main"
  }
}
```

Resposta imediata:

```json
{
  "type": "res",
  "id": "2",
  "ok": true,
  "payload": {
    "runId": "uuid",
    "acceptedAt": 1234567890.0,
    "status": "accepted"
  }
}
```

Eventos streamados:

- `assistant` — texto da resposta
- `tool` — início/fim de execução de tool
- `lifecycle` — `phase: "start" | "end" | "error"`

#### agent.wait

Aguarda o fim de um run.

```json
{
  "type": "req",
  "id": "3",
  "method": "agent.wait",
  "params": {
    "runId": "uuid",
    "timeoutMs": 30000
  }
}
```

#### health

Status do gateway e lit serve.

```json
{
  "type": "req",
  "id": "4",
  "method": "health",
  "params": {}
}
```

## CLI

```bash
# Iniciar gateway
liteclaw gateway [--port 18789] [--host 127.0.0.1] [--model gemma3-1b] [--verbose]

# Enviar mensagem (gateway deve estar rodando)
liteclaw agent -m "Mensagem" [--gateway-url ws://127.0.0.1:18789/ws] [--session main]
```
