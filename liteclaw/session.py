"""
 * @author João Gabriel de Almeida
 """

"""Gerenciador de sessões para o agente LiteClaw."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class SessionManager:
    """
    Gerencia sessões de chat com persistência.
    Cada sessão tem um sessionKey (ex: main, telegram:123) e mantém histórico.
    """

    def __init__(
        self,
        workspace_dir: Optional[Path] = None,
        persist_dir: Optional[Path] = None,
    ):
        self.workspace_dir = Path(workspace_dir or Path.home() / ".liteclaw" / "workspace")
        self.persist_dir = Path(persist_dir or Path.home() / ".liteclaw" / "sessions")
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, List[Dict[str, Any]]] = {}

    def _session_file(self, session_key: str) -> Path:
        """Arquivo de persistência para a sessão (sanitiza o key)."""
        safe = "".join(c if c.isalnum() or c in "-_:" else "_" for c in session_key)
        return self.persist_dir / f"{safe}.json"

    def get_messages(self, session_key: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retorna o histórico de mensagens da sessão."""
        if session_key in self._cache:
            msgs = self._cache[session_key]
        else:
            path = self._session_file(session_key)
            if path.exists():
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    msgs = data.get("messages", [])
                except (json.JSONDecodeError, OSError):
                    msgs = []
            else:
                msgs = []
            self._cache[session_key] = msgs

        if limit:
            return msgs[-limit:]
        return list(msgs)

    def append_messages(
        self,
        session_key: str,
        messages: List[Dict[str, Any]],
        persist: bool = True,
    ) -> None:
        """Adiciona mensagens ao histórico e persiste."""
        if session_key not in self._cache:
            self._cache[session_key] = self.get_messages(session_key, limit=None)
        self._cache[session_key].extend(messages)

        if persist:
            self._save(session_key)

    def set_messages(
        self,
        session_key: str,
        messages: List[Dict[str, Any]],
        persist: bool = True,
    ) -> None:
        """Substitui o histórico da sessão."""
        self._cache[session_key] = list(messages)
        if persist:
            self._save(session_key)

    def _save(self, session_key: str) -> None:
        """Persiste a sessão em disco."""
        if session_key not in self._cache:
            return
        path = self._session_file(session_key)
        data = {
            "sessionKey": session_key,
            "messages": self._cache[session_key],
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def clear(self, session_key: str) -> None:
        """Limpa o histórico da sessão."""
        self._cache[session_key] = []
        self._save(session_key)

    def get_bootstrap_files(self) -> Dict[str, str]:
        """
        Retorna conteúdo dos arquivos de bootstrap (AGENTS.md, SOUL.md, TOOLS.md).
        Procurar em workspace_dir.
        """
        result: Dict[str, str] = {}
        for name in ("AGENTS.md", "SOUL.md", "TOOLS.md"):
            path = self.workspace_dir / name
            if path.exists():
                result[name] = path.read_text(encoding="utf-8", errors="replace")
        return result
