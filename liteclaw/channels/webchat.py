"""
 * @author João Gabriel de Almeida
 """

"""Canal WebChat - mensagens via Gateway WebSocket (já integrado na UI)."""

from liteclaw.channels.base import Channel, Message


class WebChatChannel(Channel):
    """
    O WebChat é servido pelo Gateway e as mensagens já fluem
    via agent RPC. Este canal é um placeholder para consistência.
    """

    async def connect(self) -> None:
        pass

    async def disconnect(self) -> None:
        pass

    async def send(self, session_key: str, text: str, **kwargs: Any) -> bool:
        return True
