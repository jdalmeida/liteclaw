"""
 * @author João Gabriel de Almeida
 """

"""Tools built-in inspiradas no OpenClaw: exec, read, write, edit, web_fetch, web_search."""

import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from liteclaw.tools import tool

# Grupos de tools para perfis
TOOL_GROUPS = {
    "group:fs": ["read", "write", "edit"],
    "group:runtime": ["exec", "bash"],
    "group:web": ["web_fetch", "web_search"],
}


def _resolve_path(path: str, workspace: Path) -> Path:
    """Resolve path relativo ao workspace, evitando escape."""
    p = Path(path)
    if not p.is_absolute():
        p = workspace / p
    try:
        return p.resolve().relative_to(workspace.resolve())
    except ValueError:
        raise PermissionError(f"Path fora do workspace: {path}")
    return workspace / p


@tool(description="Lê o conteúdo de um arquivo no workspace")
def read(path: str, workspace: Optional[str] = None) -> Dict[str, Any]:
    """
    Lê o conteúdo de um arquivo.
    path: caminho relativo ao workspace
    """
    ws = Path(workspace or os.environ.get("LITECLAW_WORKSPACE", str(Path.home() / ".liteclaw" / "workspace")))
    full = ws / path
    if not full.exists():
        return {"error": f"Arquivo não encontrado: {path}"}
    if full.is_dir():
        return {"error": f"É um diretório: {path}"}
    try:
        content = full.read_text(encoding="utf-8", errors="replace")
        return {"path": path, "content": content}
    except Exception as e:
        return {"error": str(e)}


@tool(description="Escreve conteúdo em um arquivo no workspace")
def write(path: str, content: str, workspace: Optional[str] = None) -> Dict[str, Any]:
    """
    Escreve conteúdo em um arquivo. Cria o arquivo se não existir.
    path: caminho relativo ao workspace
    """
    ws = Path(workspace or os.environ.get("LITECLAW_WORKSPACE", str(Path.home() / ".liteclaw" / "workspace")))
    full = ws / path
    try:
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding="utf-8")
        return {"path": path, "status": "written"}
    except Exception as e:
        return {"error": str(e)}


@tool(description="Edita um arquivo aplicando instruções de edição")
def edit(
    path: str,
    instructions: str,
    workspace: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Edita um arquivo conforme instruções.
    instructions: descrição da edição a ser feita (o modelo deve ser preciso)
    """
    ws = Path(workspace or os.environ.get("LITECLAW_WORKSPACE", str(Path.home() / ".liteclaw" / "workspace")))
    full = ws / path
    if not full.exists():
        return {"error": f"Arquivo não encontrado: {path}"}
    try:
        content = full.read_text(encoding="utf-8", errors="replace")
        # Edição simples: por ora retornamos o conteúdo para o modelo editar
        # e usar write. Uma implementação mais sofisticada usaria um diff.
        return {
            "path": path,
            "current_content": content,
            "instructions": instructions,
            "hint": "Use a tool 'write' com o conteúdo editado após aplicar as instruções",
        }
    except Exception as e:
        return {"error": str(e)}


@tool(name="exec", description="Executa um comando no shell (workspace como cwd)")
def run_exec(
    command: str,
    workspace: Optional[str] = None,
    timeout: Optional[int] = 1800,
) -> Dict[str, Any]:
    """
    Executa um comando no shell.
    command: comando a executar
    timeout: timeout em segundos (default 1800)
    """
    ws = Path(workspace or os.environ.get("LITECLAW_WORKSPACE", str(Path.home() / ".liteclaw" / "workspace")))
    ws.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(ws),
            capture_output=True,
            text=True,
            timeout=timeout or 1800,
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"error": "Timeout", "returncode": -1}
    except Exception as e:
        return {"error": str(e), "returncode": -1}


@tool(description="Alias para exec - executa comando bash")
def bash(command: str, workspace: Optional[str] = None, timeout: Optional[int] = 1800) -> Dict[str, Any]:
    """Executa comando no bash."""
    return run_exec(command, workspace, timeout)


@tool(description="Busca conteúdo de uma URL e extrai texto")
def web_fetch(
    url: str,
    max_chars: Optional[int] = 50000,
    extract_mode: str = "text",
) -> Dict[str, Any]:
    """
    Busca o conteúdo de uma URL.
    url: URL a buscar
    max_chars: máximo de caracteres a retornar
    extract_mode: 'text' ou 'markdown'
    """
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        text = resp.text
        if len(text) > (max_chars or 50000):
            text = text[: max_chars or 50000] + "\n...[truncado]"
        return {"url": url, "content": text, "status": resp.status_code}
    except requests.RequestException as e:
        return {"error": str(e), "url": url}
    except Exception as e:
        return {"error": str(e), "url": url}


@tool(description="Busca na web via Brave Search API (requer BRAVE_API_KEY)")
def web_search(query: str, count: int = 5) -> Dict[str, Any]:
    """
    Busca na web usando Brave Search API.
    query: termo de busca
    count: número de resultados (1-10)
    """
    api_key = os.environ.get("BRAVE_API_KEY")
    if not api_key:
        return {"error": "BRAVE_API_KEY não configurada"}
    try:
        resp = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": query, "count": min(max(count, 1), 10)},
            headers={"X-Subscription-Token": api_key},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        results = []
        for r in data.get("web", {}).get("results", [])[: count]:
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "description": r.get("description", ""),
            })
        return {"query": query, "results": results}
    except requests.RequestException as e:
        return {"error": str(e), "query": query}
    except Exception as e:
        return {"error": str(e), "query": query}


def register_builtin_tools(registry: Any, workspace: Optional[Path] = None) -> None:
    """Registra todas as tools builtin no registry."""
    registry.register(read)
    registry.register(write)
    registry.register(edit)
    registry.register(run_exec)
    registry.register(bash)
    registry.register(web_fetch)
    registry.register(web_search)
