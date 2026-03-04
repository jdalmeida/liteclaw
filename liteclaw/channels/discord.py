"""
 * @author João Gabriel de Almeida
 """

"""Canal Discord para LiteClaw."""

from typing import Any, Dict, List, Optional

from liteclaw.channels.base import Channel, Message


class DiscordChannel(Channel):
    """Canal Discord via discord.py."""

    def __init__(
        self,
        token: str,
        allow_from: Optional[List[str]] = None,
        agent_callback: Optional[Any] = None,
    ):
        self.token = token
        self.allow_from = allow_from or ["*"]
        self.agent_callback = agent_callback
        self._client = None

    def _is_allowed(self, user_id: int, username: Optional[str]) -> bool:
        if "*" in self.allow_from:
            return True
        uid = str(user_id)
        if uid in self.allow_from:
            return True
        if username and username in self.allow_from:
            return True
        return False

    async def connect(self) -> None:
        import discord

        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        bot = discord.Client(intents=intents)

        @bot.event
        async def on_ready():
            pass

        @bot.event
        async def on_message(message: discord.Message):
            if message.author.bot:
                return
            if not message.content:
                return
            user = message.author
            if not self._is_allowed(user.id, user.name):
                return
            session_key = f"discord:{message.channel.id}:{user.id}"
            msg = Message(
                session_key=session_key,
                text=message.content,
                channel="discord",
                peer_id=str(user.id),
                peer_name=user.name,
                extra={"channel_id": message.channel.id},
            )
            self._dispatch_message(msg)
            if self.agent_callback:
                result = await self.agent_callback(msg)
                if result:
                    await message.channel.send(str(result)[:2000])

        self._client = bot
        await bot.start(self.token)

    async def disconnect(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None

    async def send(self, session_key: str, text: str, **kwargs: Any) -> bool:
        if not self._client or not session_key.startswith("discord:"):
            return False
        parts = session_key.split(":")
        if len(parts) < 3:
            return False
        channel_id = int(parts[1])
        try:
            channel = self._client.get_channel(channel_id)
            if channel:
                await channel.send(text[:2000])
                return True
        except Exception:
            pass
        return False
