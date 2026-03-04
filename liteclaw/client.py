"""
 * @author João Gabriel de Almeida
 """

"""Cliente Python para LiteRT-LM com suporte a tools."""

import json
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import requests

from liteclaw.tools import ToolRegistry


class LiteClawClient:
    """
    Cliente para interagir com modelos LiteRT-LM locais via API Gemini-compatible.

    Gerencia o servidor `lit serve` e permite chamadas com suporte a tools
    (function calling).
    """

    def __init__(
        self,
        model: str = "gemma3-1b",
        lit_path: Optional[Union[str, Path]] = None,
        port: int = 9379,
        base_url: Optional[str] = None,
        auto_start: bool = True,
        backend: str = "cpu",
    ):
        """
        Args:
            model: ID do modelo (ex: gemma3-1b, qwen2.5-1.5b)
            lit_path: Caminho para o executável lit (default: ./lit no cwd)
            port: Porta do servidor
            base_url: URL base da API (default: http://localhost:{port})
            auto_start: Iniciar servidor automaticamente se não estiver rodando
            backend: Backend de inferência (cpu, gpu)
        """
        self.model = model
        self.port = port
        self.base_url = base_url or f"http://localhost:{port}"
        self.auto_start = auto_start
        self.backend = backend
        if lit_path:
            self._lit_path = Path(lit_path)
        else:
            # Procura lit no mesmo diretório do pacote liteclaw
            self._lit_path = Path(__file__).resolve().parent.parent / "lit"
        self._process: Optional[subprocess.Popen] = None
        self.tools = ToolRegistry()

    def _ensure_server(self) -> None:
        """Garante que o servidor está rodando."""
        if self._process is not None:
            if self._process.poll() is None:
                return
            self._process = None

        try:
            r = requests.get(f"{self.base_url}/", timeout=2)
        except requests.RequestException:
            pass
        else:
            if r.status_code != 404:
                return

        if not self.auto_start:
            raise RuntimeError(
                "Servidor não está rodando. Inicie com 'lit serve' ou use auto_start=True"
            )

        self.start_server()

    def start_server(self) -> None:
        """Inicia o servidor lit em background."""
        if self._process is not None and self._process.poll() is None:
            return

        cmd = [str(self._lit_path), "serve", "-p", str(self.port)]
        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            cwd=str(self._lit_path.parent),
        )

        for _ in range(30):
            time.sleep(1)
            try:
                requests.get(f"{self.base_url}/", timeout=1)
                break
            except requests.RequestException:
                if self._process.poll() is not None:
                    _, err = self._process.communicate()
                    raise RuntimeError(
                        f"Falha ao iniciar lit serve: {err.decode()}"
                    )
        else:
            self.stop_server()
            raise RuntimeError("Timeout ao iniciar o servidor lit")

    def stop_server(self) -> None:
        """Para o servidor lit."""
        if self._process is not None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None

    def generate_content(
        self,
        contents: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Envia uma requisição para generateContent.

        Args:
            contents: Lista de mensagens no formato Gemini
            tools: Definições de tools (usa self.tools se None)
            tool_config: Configuração de tools (ex: functionCallingConfig)

        Returns:
            Resposta da API
        """
        self._ensure_server()

        url = f"{self.base_url}/v1beta/models/{self.model}:generateContent"
        payload: Dict[str, Any] = {"contents": contents}

        if tools is None and self.tools._tools:
            tools = self.tools.get_gemini_format()
        if tools:
            payload["tools"] = tools
            if tool_config is None:
                tool_config = {
                    "functionCallingConfig": {
                        "mode": "AUTO",
                    }
                }
        if tool_config:
            payload["toolConfig"] = tool_config

        response = requests.post(
            url,
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
        return response.json()

    def chat(
        self,
        message: str,
        history: Optional[List[Dict[str, Any]]] = None,
        max_tool_rounds: int = 5,
    ) -> str:
        """
        Envia uma mensagem e processa a resposta, executando tools automaticamente.

        Args:
            message: Mensagem do usuário
            history: Histórico de conversa (opcional)
            max_tool_rounds: Máximo de rodadas de tool calling

        Returns:
            Resposta final em texto
        """
        contents = history or []
        contents.append({
            "role": "user",
            "parts": [{"text": message}],
        })

        for _ in range(max_tool_rounds):
            response = self.generate_content(contents)
            candidates = response.get("candidates", [])
            if not candidates:
                return "Sem resposta do modelo."

            content = candidates[0].get("content", {})
            parts = content.get("parts", [])

            text_parts = []
            tool_calls = []

            for part in parts:
                if "text" in part:
                    text_parts.append(part["text"])
                if "functionCall" in part:
                    fc = part["functionCall"]
                    args = fc.get("args") or {}
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            args = {}
                    tool_calls.append({
                        "name": fc.get("name", ""),
                        "args": args,
                    })

            if text_parts and not tool_calls:
                return "\n".join(text_parts)

            if not tool_calls:
                return "\n".join(text_parts) if text_parts else "Sem resposta."

            tool_parts = []
            for tc in tool_calls:
                result = self.tools.call(tc["name"], tc["args"])
                tool_parts.append({
                    "functionResponse": {
                        "name": tc["name"],
                        "response": result,
                    }
                })

            contents.append({
                "role": "model",
                "parts": parts,
            })
            contents.append({
                "role": "user",
                "parts": tool_parts,
            })

        return "Limite de rodadas de tools atingido."

    def __enter__(self) -> "LiteClawClient":
        if self.auto_start:
            self.start_server()
        return self

    def __exit__(self, *args) -> None:
        self.stop_server()
