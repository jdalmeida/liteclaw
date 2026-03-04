"""
 * @author João Gabriel de Almeida
 """

"""Protocolo WebSocket simplificado compatível com OpenClaw."""

from typing import Any, Dict, Optional


def make_request(req_id: str, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Cria um frame de request."""
    return {
        "type": "req",
        "id": req_id,
        "method": method,
        "params": params or {},
    }


def make_response(req_id: str, ok: bool, payload: Any = None, error: Optional[str] = None) -> Dict[str, Any]:
    """Cria um frame de response."""
    out = {"type": "res", "id": req_id, "ok": ok}
    if ok:
        out["payload"] = payload or {}
    else:
        out["error"] = error or "Unknown error"
    return out


def make_event(event: str, payload: Any = None) -> Dict[str, Any]:
    """Cria um frame de event."""
    return {
        "type": "event",
        "event": event,
        "payload": payload or {},
    }
