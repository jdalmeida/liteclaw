"""
 * @author João Gabriel de Almeida
 """

"""Fila de comandos por sessão para serialização de runs."""

import asyncio
from typing import Any, Callable, Coroutine, Dict, Optional


class SessionQueue:
    """
    Fila por session_key. Garante que apenas um run por sessão executa por vez.
    """

    def __init__(self):
        self._queues: Dict[str, asyncio.Queue] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._running: Dict[str, bool] = {}

    def _get_lock(self, session_key: str) -> asyncio.Lock:
        if session_key not in self._locks:
            self._locks[session_key] = asyncio.Lock()
        return self._locks[session_key]

    async def run_serialized(
        self,
        session_key: str,
        coro: Coroutine,
    ) -> Any:
        """
        Executa a coroutine de forma serializada por session_key.
        Outros runs da mesma sessão esperam na fila.
        """
        lock = self._get_lock(session_key)
        async with lock:
            return await coro
