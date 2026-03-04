"""
 * @author João Gabriel de Almeida
 """

"""Loop de agente autônomo para o LiteClaw."""

import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from liteclaw.client import LiteClawClient
from liteclaw.session import SessionManager
from liteclaw.skills import SkillsLoader, Skill
from liteclaw.tools import ToolRegistry


def _build_system_prompt(
    bootstrap: Dict[str, str],
    skills: List[Skill],
    skills_prompt: str,
) -> str:
    """Monta o system prompt a partir de bootstrap e skills."""
    parts: List[str] = []

    if bootstrap.get("AGENTS.md"):
        parts.append(bootstrap["AGENTS.md"])
    if bootstrap.get("SOUL.md"):
        parts.append(bootstrap["SOUL.md"])
    if bootstrap.get("TOOLS.md"):
        parts.append(bootstrap["TOOLS.md"])

    if skills_prompt:
        parts.append("\n## Skills disponíveis\n")
        parts.append(skills_prompt)

    return "\n\n".join(parts) if parts else ""


class Agent:
    """
    Loop de agente: intake → context → model → tools → stream → persist.
    Usa LiteClawClient para inferência e ToolRegistry para execução de tools.
    """

    def __init__(
        self,
        client: LiteClawClient,
        session_manager: Optional[SessionManager] = None,
        skills_loader: Optional[SkillsLoader] = None,
        workspace_dir: Optional[Path] = None,
        config: Optional[Dict[str, Any]] = None,
        max_tool_rounds: int = 5,
        timeout_seconds: int = 600,
    ):
        self.client = client
        self.config = config or {}
        self.workspace_dir = Path(workspace_dir or Path.home() / ".liteclaw" / "workspace")
        self.max_tool_rounds = max_tool_rounds
        self.timeout_seconds = timeout_seconds

        self.session_manager = session_manager or SessionManager(
            workspace_dir=self.workspace_dir,
        )
        self.skills_loader = skills_loader or SkillsLoader(
            workspace_dir=self.workspace_dir,
            config=self.config,
        )

        self._skills_snapshot: Optional[List[Skill]] = None
        self._system_prompt: Optional[str] = None

    def _get_skills_snapshot(self) -> List[Skill]:
        """Carrega ou reutiliza snapshot de skills."""
        if self._skills_snapshot is None:
            self._skills_snapshot = self.skills_loader.load()
        return self._skills_snapshot

    def _get_system_prompt(self) -> str:
        """Monta o system prompt com bootstrap e skills."""
        if self._system_prompt is not None:
            return self._system_prompt
        bootstrap = self.session_manager.get_bootstrap_files()
        skills = self._get_skills_snapshot()
        skills_prompt = SkillsLoader.format_for_prompt(skills)
        self._system_prompt = _build_system_prompt(bootstrap, skills, skills_prompt)
        return self._system_prompt

    def _contents_with_system(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Converte mensagens para formato Gemini com system instruction.
        A API Gemini usa systemInstruction no payload, não em contents.
        """
        system = system_prompt or self._get_system_prompt()
        if not system:
            return messages

        # Gemini: systemInstruction pode ser passado no generateContent
        # Por ora, injetamos como primeira mensagem do user se for necessário
        # O lit serve pode usar systemInstruction - verificar API
        # Por compatibilidade, adicionamos como primeira mensagem do modelo
        # ou como parte do generateContent
        return messages

    def run(
        self,
        message: str,
        session_key: str = "main",
        history: Optional[List[Dict[str, Any]]] = None,
        stream_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ) -> str:
        """
        Executa um turno do agente: recebe mensagem, processa com tools, retorna resposta.

        Args:
            message: Mensagem do usuário
            session_key: Identificador da sessão
            history: Histórico override (se None, usa session_manager)
            stream_callback: callback(event_type, payload) para streaming

        Returns:
            Resposta final em texto
        """
        if history is None:
            history = self.session_manager.get_messages(session_key)

        contents = list(history)
        user_msg = {"role": "user", "parts": [{"text": message}]}
        contents.append(user_msg)
        new_start = len(history)  # índice onde começam as mensagens novas

        system_prompt = self._get_system_prompt()

        for round_num in range(self.max_tool_rounds):
            if stream_callback:
                stream_callback("lifecycle", {"phase": "start", "round": round_num + 1})

            response = self._generate_with_system(contents, system_prompt)

            candidates = response.get("candidates", [])
            if not candidates:
                if stream_callback:
                    stream_callback("lifecycle", {"phase": "error", "error": "Sem resposta"})
                return "Sem resposta do modelo."

            content = candidates[0].get("content", {})
            parts = content.get("parts", [])

            text_parts: List[str] = []
            tool_calls: List[Dict[str, Any]] = []

            for part in parts:
                if "text" in part:
                    text_parts.append(part["text"])
                    if stream_callback:
                        stream_callback("assistant", {"text": part["text"]})
                if "functionCall" in part:
                    fc = part["functionCall"]
                    args = fc.get("args") or {}
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            args = {}
                    tool_calls.append({"name": fc.get("name", ""), "args": args})

            if text_parts and not tool_calls:
                final = "\n".join(text_parts)
                contents.append({"role": "model", "parts": parts})
                self.session_manager.append_messages(session_key, contents[new_start:])
                if stream_callback:
                    stream_callback("lifecycle", {"phase": "end"})
                return final

            if not tool_calls:
                final = "\n".join(text_parts) if text_parts else "Sem resposta."
                contents.append({"role": "model", "parts": parts})
                self.session_manager.append_messages(session_key, contents[new_start:])
                if stream_callback:
                    stream_callback("lifecycle", {"phase": "end"})
                return final

            tool_parts = []
            for tc in tool_calls:
                if stream_callback:
                    stream_callback("tool", {"name": tc["name"], "args": tc["args"], "phase": "start"})
                result = self.client.tools.call(tc["name"], tc["args"])
                if stream_callback:
                    stream_callback("tool", {"name": tc["name"], "result": result, "phase": "end"})
                tool_parts.append({
                    "functionResponse": {
                        "name": tc["name"],
                        "response": result,
                    }
                })

            contents.append({"role": "model", "parts": parts})
            contents.append({"role": "user", "parts": tool_parts})
            # Persistir a cada rodada para manter contexto em caso de timeout
            self.session_manager.set_messages(session_key, contents)

        if stream_callback:
            stream_callback("lifecycle", {"phase": "error", "error": "Limite de rodadas"})
        return "Limite de rodadas de tools atingido."

    def _generate_with_system(
        self,
        contents: List[Dict[str, Any]],
        system_prompt: str,
    ) -> Dict[str, Any]:
        """
        Chama generate_content injetando system instruction.
        O lit serve (API Gemini) pode suportar systemInstruction no payload.
        """
        import requests
        self.client._ensure_server()
        url = f"{self.client.base_url}/v1beta/models/{self.client.model}:generateContent"
        payload: Dict[str, Any] = {"contents": contents}
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}
        if self.client.tools._tools:
            payload["tools"] = self.client.tools.get_gemini_format()
            payload["toolConfig"] = {
                "functionCallingConfig": {"mode": "AUTO"},
            }
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()
