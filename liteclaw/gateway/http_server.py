"""
 * @author João Gabriel de Almeida
 """

"""Servidor HTTP + WebSocket combinado para o Gateway LiteClaw."""

import asyncio
import json
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Set

from aiohttp import web
from aiohttp.web import Request, WebSocketResponse

from liteclaw.agent import Agent
from liteclaw.client import LiteClawClient
from liteclaw.gateway.protocol import make_event, make_response
from liteclaw.gateway.queue import SessionQueue
from liteclaw.session import SessionManager
from liteclaw.skills import SkillsLoader
from liteclaw.tools_builtin import register_builtin_tools


def _get_web_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "web"


def _load_config() -> Dict[str, Any]:
    """Carrega config de ~/.liteclaw/config.json."""
    path = Path.home() / ".liteclaw" / "config.json"
    if path.exists():
        try:
            import json
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


class GatewayServer:
    """
    Servidor HTTP + WebSocket.
    - GET / -> WebChat (index.html)
    - GET /ws -> WebSocket do gateway
    Porta padrão 18789.
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
        self.config = config if config is not None else _load_config()
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
        self._clients: Set[WebSocketResponse] = set()
        self._runs: Dict[str, Dict[str, Any]] = {}
        self._app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None
        self._channel_tasks: list = []

    async def _health(self) -> Dict[str, Any]:
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
        ws: WebSocketResponse,
        run_id: str,
    ) -> Dict[str, Any]:
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

    async def _send_event(self, ws: WebSocketResponse, event: str, payload: Dict[str, Any]) -> None:
        try:
            if not ws.closed:
                await ws.send_str(json.dumps(make_event(event, payload)))
        except Exception:
            pass

    async def _handle_connect(self, params: Dict[str, Any]) -> Dict[str, Any]:
        health = await self._health()
        return {
            "status": "ok",
            "snapshot": {"presence": {}, "health": health},
        }

    async def _handle_agent(self, ws: WebSocketResponse, params: Dict[str, Any]) -> Dict[str, Any]:
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
        return {"status": "ok", "note": "Channels not yet connected"}

    async def _ws_handler(self, request: Request) -> WebSocketResponse:
        ws = WebSocketResponse()
        await ws.prepare(request)
        self._clients.add(ws)
        connected = False
        try:
            async for msg in ws:
                if msg.type != web.WSMsgType.TEXT:
                    continue
                try:
                    data = json.loads(msg.data)
                except json.JSONDecodeError:
                    await ws.send_str(json.dumps(make_response("", False, error="Invalid JSON")))
                    continue
                if data.get("type") != "req":
                    continue
                msg_id = data.get("id", "")
                method = data.get("method", "")
                params = data.get("params", {})
                if method == "connect":
                    payload = await self._handle_connect(params)
                    await ws.send_str(json.dumps(make_response(msg_id, True, payload)))
                    connected = True
                elif not connected:
                    await ws.send_str(json.dumps(make_response(msg_id, False, error="Connect first")))
                else:
                    try:
                        if method == "agent":
                            payload = await self._handle_agent(ws, params)
                        elif method == "agent.wait":
                            payload = await self._handle_agent_wait(params)
                        elif method == "health":
                            payload = await self._health()
                        elif method == "send":
                            payload = await self._handle_send(params)
                        else:
                            await ws.send_str(json.dumps(make_response(msg_id, False, error=f"Unknown method: {method}")))
                            continue
                        await ws.send_str(json.dumps(make_response(msg_id, True, payload)))
                    except Exception as e:
                        await ws.send_str(json.dumps(make_response(msg_id, False, error=str(e))))
        finally:
            self._clients.discard(ws)
        return ws

    async def _index_handler(self, request: Request) -> web.Response:
        path = _get_web_dir() / "index.html"
        return web.FileResponse(path)

    async def _app_js_handler(self, request: Request) -> web.Response:
        path = _get_web_dir() / "app.js"
        return web.FileResponse(path)

    async def _agent_for_message(self, msg) -> str:
        """Executa o agente para uma mensagem de canal e retorna a resposta."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.agent.run(msg.text, session_key=msg.session_key),
        )

    async def _start_channels(self, app: web.Application) -> None:
        """Inicia os canais configurados."""
        channels_cfg = self.config.get("channels", {})
        tg = channels_cfg.get("telegram", {})
        if tg.get("botToken"):
            from liteclaw.channels.telegram import TelegramChannel
            ch = TelegramChannel(
                bot_token=tg["botToken"],
                allow_from=tg.get("allowFrom", ["*"]),
                agent_callback=self._agent_for_message,
            )
            task = asyncio.create_task(ch.connect())
            self._channel_tasks.append((ch, task))
        dc = channels_cfg.get("discord", {})
        if dc.get("token"):
            from liteclaw.channels.discord import DiscordChannel
            ch = DiscordChannel(
                token=dc["token"],
                allow_from=dc.get("allowFrom", ["*"]),
                agent_callback=self._agent_for_message,
            )
            task = asyncio.create_task(ch.connect())
            self._channel_tasks.append((ch, task))

    def _create_app(self) -> web.Application:
        app = web.Application()
        app.router.add_get("/", self._index_handler)
        app.router.add_get("/ws", self._ws_handler)
        app.router.add_get("/app.js", self._app_js_handler)
        app.on_startup.append(self._start_channels)
        return app

    def start(self) -> None:
        app = self._create_app()
        web.run_app(app, host=self.host, port=self.port)
