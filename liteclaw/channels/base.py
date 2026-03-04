"""
 * @author João Gabriel de Almeida
 """

"""Interface base para canais de mensagem."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional


@dataclass
class Message:
    """Mensagem recebida de um canal."""
    session_key: str
    text: str
    channel: str
    peer_id: str
    peer_name: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None


class Channel(ABC):
    """
    Interface para canais de mensagem.
    connect(), disconnect(), send(), on_message(callback)
    """

    @abstractmethod
    async def connect(self) -> None:
        """Conecta ao canal."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Desconecta do canal."""
        pass

    @abstractmethod
    async def send(self, session_key: str, text: str, **kwargs: Any) -> bool:
        """Envia mensagem para a sessão no canal."""
        pass

    def set_message_callback(self, callback: Callable[[Message], Any]) -> None:
        """Define callback chamado quando mensagem é recebida."""
        self._on_message = callback

    def _dispatch_message(self, msg: Message) -> None:
        """Chama o callback de mensagem."""
        if hasattr(self, "_on_message") and self._on_message:
            self._on_message(msg)
