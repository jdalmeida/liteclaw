"""
 * @author João Gabriel de Almeida
 """

"""Canal Telegram para LiteClaw."""

import asyncio
from typing import Any, Dict, Optional

from liteclaw.channels.base import Channel, Message


class TelegramChannel(Channel):
    """Canal Telegram via python-telegram-bot."""

    def __init__(
        self,
        bot_token: str,
        allow_from: Optional[list] = None,
        agent_callback: Optional[Any] = None,
    ):
        self.bot_token = bot_token
        self.allow_from = allow_from or ["*"]
        self.agent_callback = agent_callback
        self._application = None

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
        from telegram import Update
        from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

        async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            if not update.message or not update.message.text:
                return
            user = update.effective_user
            if not user or not self._is_allowed(user.id, user.username):
                await update.message.reply_text("Acesso não autorizado.")
                return
            session_key = f"telegram:{user.id}"
            msg = Message(
                session_key=session_key,
                text=update.message.text,
                channel="telegram",
                peer_id=str(user.id),
                peer_name=user.username or user.first_name,
            )
            self._dispatch_message(msg)
            if self.agent_callback:
                result = await self.agent_callback(msg)
                if result:
                    await update.message.reply_text(str(result)[:4000])

        app = Application.builder().token(self.bot_token).build()
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        self._application = app
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)

    async def disconnect(self) -> None:
        if self._application:
            await self._application.updater.stop()
            await self._application.stop()
            await self._application.shutdown()
            self._application = None

    async def send(self, session_key: str, text: str, **kwargs: Any) -> bool:
        if not self._application or not session_key.startswith("telegram:"):
            return False
        chat_id = session_key.split(":", 1)[1]
        try:
            await self._application.bot.send_message(chat_id=chat_id, text=text[:4000])
            return True
        except Exception:
            return False
