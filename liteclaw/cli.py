"""
 * @author João Gabriel de Almeida
 """

"""CLI do LiteClaw."""

import argparse
import asyncio
import json
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(prog="liteclaw", description="LiteClaw - Agente local com LLM")
    sub = parser.add_subparsers(dest="cmd", help="Comando")

    # gateway
    p_gw = sub.add_parser("gateway", help="Inicia o Gateway WebSocket")
    p_gw.add_argument("--port", type=int, default=18789, help="Porta do gateway")
    p_gw.add_argument("--host", default="127.0.0.1", help="Host de bind")
    p_gw.add_argument("--model", default="gemma3-1b", help="Modelo LiteRT-LM")
    p_gw.add_argument("--verbose", "-v", action="store_true", help="Log verboso")

    # agent (chat direto)
    p_agent = sub.add_parser("agent", help="Envia mensagem ao agente (modo direto)")
    p_agent.add_argument("--message", "-m", required=True, help="Mensagem")
    p_agent.add_argument("--gateway-url", default="ws://127.0.0.1:18789/ws", help="URL do gateway WebSocket")
    p_agent.add_argument("--session", default="main", help="Session key")

    args = parser.parse_args()

    if args.cmd == "gateway":
        from liteclaw.gateway import GatewayServer
        server = GatewayServer(port=args.port, host=args.host, model=args.model)
        if args.verbose:
            print(f"LiteClaw Gateway em http://{args.host}:{args.port} (WebChat) e ws://{args.host}:{args.port}/ws", file=sys.stderr)
        server.start()
    elif args.cmd == "agent":
        asyncio.run(_run_agent_cmd(args))
    else:
        parser.print_help()


async def _run_agent_cmd(args) -> None:
    """Envia mensagem ao agente via gateway."""
    import websockets
    uri = args.gateway_url.replace("http", "ws")
    if not uri.endswith("/ws"):
        uri = uri.rstrip("/") + "/ws"
    async with websockets.connect(uri) as ws:
        # connect
        await ws.send(json.dumps({
            "type": "req",
            "id": "1",
            "method": "connect",
            "params": {"role": "cli", "deviceId": "cli"},
        }))
        r = json.loads(await ws.recv())
        if not r.get("ok"):
            print("Erro ao conectar:", r.get("error", r), file=sys.stderr)
            sys.exit(1)

        # agent
        await ws.send(json.dumps({
            "type": "req",
            "id": "2",
            "method": "agent",
            "params": {"message": args.message, "sessionKey": args.session},
        }))
        r = json.loads(await ws.recv())
        if not r.get("ok"):
            print("Erro:", r.get("error", r), file=sys.stderr)
            sys.exit(1)
        run_id = r.get("payload", {}).get("runId", "")
        print(f"Run iniciado: {run_id}", file=sys.stderr)

        # Consumir eventos até lifecycle end
        full_text = []
        async for raw in ws:
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if data.get("type") == "event":
                ev = data.get("event", "")
                pl = data.get("payload", {})
                if ev == "assistant" and "text" in pl:
                    print(pl["text"], end="", flush=True)
                    full_text.append(pl["text"])
                elif ev == "lifecycle" and pl.get("phase") in ("end", "error"):
                    break
        print()
