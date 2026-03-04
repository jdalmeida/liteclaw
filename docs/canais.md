# Canais

Canais são integrações com plataformas de mensagem. O LiteClaw suporta:

- **WebChat** — integrado ao Gateway (sem config adicional)
- **Telegram** — via Bot API
- **Discord** — via discord.py

## Configuração

Em `~/.liteclaw/config.json`:

```json
{
  "channels": {
    "telegram": {
      "botToken": "SEU_BOT_TOKEN",
      "allowFrom": ["*"]
    },
    "discord": {
      "token": "SEU_BOT_TOKEN",
      "allowFrom": ["*"]
    }
  }
}
```

### allowFrom

Lista de IDs ou usernames autorizados. Use `["*"]` para permitir todos.

- **Telegram:** user ID (número) ou username
- **Discord:** user ID ou username

## Telegram

1. Crie um bot com [@BotFather](https://t.me/BotFather)
2. Obtenha o token
3. Adicione em `channels.telegram.botToken`
4. Reinicie o gateway

O bot responde a mensagens de texto (exceto comandos).

## Discord

1. Crie uma aplicação em [Discord Developer Portal](https://discord.com/developers/applications)
2. Crie um bot e copie o token
3. Habilite **Message Content Intent**
4. Adicione em `channels.discord.token`
5. Reinicie o gateway

O bot responde a mensagens em canais onde tem acesso.

## Session key

Cada canal gera um `sessionKey` único por conversa:

- **WebChat:** `main` (sessão única)
- **Telegram:** `telegram:{user_id}`
- **Discord:** `discord:{channel_id}:{user_id}`

Isso permite histórico isolado por usuário/canal.
