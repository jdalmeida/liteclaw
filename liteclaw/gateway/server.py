"""
 * @author João Gabriel de Almeida
 """

"""Servidor Gateway WebSocket para LiteClaw."""

import asyncio
import json
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Set

import websockets
from websockets.server import WebSocketServerProtocol

from liteclaw.agent import Agent
from liteclaw.client import LiteClawClient
from liteclaw.gateway.protocol import make_event, make_response
from liteclaw.gateway.queue import SessionQueue
from liteclaw.session import SessionManager
from liteclaw.skills import SkillsLoader
from liteclaw.tools_builtin import register_builtin_tools


class GatewayServer:
    """
    Servidor WebSocket que expõe o agente LiteClaw.
    Porta padrão 18789 (compatível com OpenClaw).
    """

    def __init__(
        self,
        model: str = "gemma3-1b",
        port: int = 18789,
        host: str = "127.0.0.1",
        workspace_dir: Optional[Path] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.port = port
        self.host = host
        self.config = config or {}
        self.workspace_dir = Path(workspace_dir or Path.home() / ".liteclaw" / "workspace")
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

        self.client = LiteClawClient(model=model, port=9379, auto_start=True)
        register_builtin_tools(self.client.tools)

        self.session_manager = SessionManager(workspace_dir=self.workspace_dir)
        self.skills_loader = SkillsLoader(
            workspace_dir=self.workspace_dir,
            config=self.config,
        )
        self.agent = Agent(
            client=self.client,
            session_manager=self.session_manager,
            skills_loader=self.skills_loader,
            workspace_dir=self.workspace_dir,
            config=self.config,
        )

        self.queue = SessionQueue()
        self._clients: Set[WebSocketServerProtocol] = set()
        self._runs: Dict[str, Dict[str, Any]] = {}
        self._server: Optional[websockets.WebSocketServer] = None

    async def _health(self) -> Dict[str, Any]:
        """Status do gateway e lit serve."""
        try:
            import requests
            r = requests.get(f"{self.client.base_url}/", timeout=2)
            lit_ok = r.status_code != 404
        except Exception:
            lit_ok = False
        return {
            "status": "ok" if lit_ok else "degraded",
            "litServe": "ok" if lit_ok else "unreachable",
        }

    async def _run_agent(
        self,
        session_key: str,
        message: str,
        ws: WebSocketServerProtocol,
        run_id: str,
    ) -> Dict[str, Any]:
        """Executa o agente e envia eventos via WebSocket."""
        loop = asyncio.get_event_loop()

        def stream_cb(event_type: str, payload: Dict[str, Any]) -> None:
            asyncio.run_coroutine_threadsafe(
                self._send_event(ws, event_type, payload),
                loop,
            )

        result = await loop.run_in_executor(
            None,
            lambda: self.agent.run(
                message=message,
                session_key=session_key,
                stream_callback=stream_cb,
            ),
        )
        return {"status": "ok", "result": result}

    async def _send_event(self, ws: WebSocketServerProtocol, event: str, payload: Dict[str, Any]) -> None:
        """Envia evento para um cliente."""
        try:
            if ws.open:
                await ws.send(json.dumps(make_event(event, payload)))
        except Exception:
            pass

    async def _broadcast_event(self, event: str, payload: Dict[str, Any]) -> None:
        """Envia evento para todos os clientes conectados."""
        for ws in list(self._clients):
            await self._send_event(ws, event, payload)

    async def _handle_connect(self, ws: WebSocketServerProtocol, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handshake de conexão."""
        role = params.get("role", "client")
        device_id = params.get("deviceId", "unknown")
        health = await self._health()
        return {
            "status": "ok",
            "snapshot": {
                "presence": {},
                "health": health,
            },
        }

    async def _handle_agent(
        self,
        ws: WebSocketServerProtocol,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Inicia um run do agente."""
        message = params.get("message", "")
        session_key = params.get("sessionKey", "main")
        run_id = str(uuid.uuid4())

        self._runs[run_id] = {"status": "running", "startedAt": asyncio.get_event_loop().time()}

        async def do_run():
            try:
                result = await self.queue.run_serialized(
                    session_key,
                    self._run_agent(session_key, message, ws, run_id),
                )
                self._runs[run_id]["status"] = "ok"
                self._runs[run_id]["endedAt"] = asyncio.get_event_loop().time()
                self._runs[run_id]["result"] = result
                await self._send_event(ws, "lifecycle", {"phase": "end", "runId": run_id})
            except Exception as e:
                self._runs[run_id]["status"] = "error"
                self._runs[run_id]["error"] = str(e)
                await self._send_event(ws, "lifecycle", {"phase": "error", "error": str(e), "runId": run_id})

        asyncio.create_task(do_run())

        return {"runId": run_id, "acceptedAt": asyncio.get_event_loop().time(), "status": "accepted"}

    async def _handle_agent_wait(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Espera o fim de um run."""
        run_id = params.get("runId", "")
        timeout = params.get("timeoutMs", 30000) / 1000.0
        start = asyncio.get_event_loop().time()
        while (asyncio.get_event_loop().time() - start) < timeout:
            if run_id in self._runs:
                r = self._runs[run_id]
                if r["status"] in ("ok", "error"):
                    return {
                        "status": r["status"],
                        "startedAt": r.get("startedAt"),
                        "endedAt": r.get("endedAt"),
                        "error": r.get("error"),
                    }
            await asyncio.sleep(0.2)
        return {"status": "timeout", "runId": run_id}

    async def _handle_send(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Envia mensagem para canal (placeholder - canais na Fase 4)."""
        return {"status": "ok", "note": "Channels not yet connected"}

    async def _handle_message(
        self,
        ws: WebSocketServerProtocol,
        msg_id: str,
        method: str,
        params: Dict[str, Any],
    ) -> None:
        """Despacha um request RPC."""
        handlers = {
            "connect": self._handle_connect,
            "agent": lambda p: self._handle_agent(ws, p),
            "agent.wait": self._handle_agent_wait,
            "health": lambda p: self._health(),
            "send": self._handle_send,
        }
        handler = handlers.get(method)
        if not handler:
            await ws.send(json.dumps(make_response(msg_id, False, error=f"Unknown method: {method}")))
            return
        try:
            if asyncio.iscoroutinefunction(handler):
                payload = await handler(params)
            else:
                payload = handler(params)
                if asyncio.iscoroutine(payload):
                    payload = await payload
            await ws.send(json.dumps(make_response(msg_id, True, payload)))
        except Exception as e:
            await ws.send(json.dumps(make_response(msg_id, False, error=str(e))))

    async def _handler(self, ws: WebSocketServerProtocol, path: str) -> None:
        """Handler de cada conexão WebSocket."""
        self._clients.add(ws)
        connected = False
        try:
            async for raw in ws:
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    await ws.send(json.dumps(make_response("", False, error="Invalid JSON")))
                    continue

                msg_type = data.get("type")
                if msg_type == "req":
                    msg_id = data.get("id", "")
                    method = data.get("method", "")
                    params = data.get("params", {})
                    if method == "connect":
                        await self._handle_message(ws, msg_id, method, params)
                        connected = True
                    elif connected:
                        await self._handle_message(ws, msg_id, method, params)
                    else:
                        await ws.send(json.dumps(make_response(msg_id, False, error="Connect first")))
        finally:
            self._clients.discard(ws)

    def start(self) -> None:
        """Inicia o servidor (blocking)."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._server = loop.run_until_complete(
            websockets.serve(self._handler, self.host, self.port)
        )
        loop.run_forever()

    async def start_async(self) -> websockets.WebSocketServer:
        """Inicia o servidor (async). Retorna o server."""
        return await websockets.serve(self._handler, self.host, self.port)
