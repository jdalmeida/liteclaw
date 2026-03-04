"""
 * @author João Gabriel de Almeida
 """

"""Loader de skills no formato AgentSkills para o LiteClaw."""

import json
import os
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Tuple

# PyYAML é opcional; se não estiver, usamos regex para frontmatter
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def _parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """Extrai frontmatter YAML do início do conteúdo. Retorna (metadata, body)."""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if not match:
        return {}, content

    fm_str, body = match.group(1), match.group(2)
    metadata: Dict[str, Any] = {}

    if HAS_YAML:
        try:
            metadata = yaml.safe_load(fm_str) or {}
        except Exception:
            pass
    else:
        # Fallback: parse simples para name, description, metadata
        for line in fm_str.split("\n"):
            if ":" in line:
                key, _, val = line.partition(":")
                key = key.strip().lower()
                val = val.strip()
                if key == "metadata" and val.startswith("{"):
                    try:
                        metadata["metadata"] = json.loads(val)
                    except json.JSONDecodeError:
                        pass
                elif key in ("name", "description"):
                    metadata[key] = val.strip('"').strip("'")

    return metadata, body.strip()


def _check_bins(bins: List[str]) -> bool:
    """Verifica se todos os binários estão no PATH."""
    for b in bins:
        if not shutil.which(b):
            return False
    return True


def _check_env(env_vars: List[str]) -> bool:
    """Verifica se todas as variáveis de ambiente existem."""
    for e in env_vars:
        if not os.environ.get(e):
            return False
    return True


def _check_config(config_paths: List[str], config: Dict[str, Any]) -> bool:
    """Verifica se os caminhos de config são truthy (nested keys com notação de ponto)."""
    for path in config_paths:
        obj = config
        for key in path.split("."):
            obj = obj.get(key) if isinstance(obj, dict) else None
            if obj is None:
                return False
        if not obj:
            return False
    return True


def _is_skill_eligible(
    skill_meta: Dict[str, Any],
    config: Optional[Dict[str, Any]] = None,
    os_filter: Optional[List[str]] = None,
) -> bool:
    """
    Verifica se a skill passa nos gates de requires.
    metadata.openclaw.requires: bins, env, config, anyBins
    metadata.openclaw.always: true ignora outros gates
    """
    config = config or {}
    meta = skill_meta.get("metadata", {})
    if isinstance(meta, str):
        try:
            meta = json.loads(meta) if meta.startswith("{") else {}
        except json.JSONDecodeError:
            meta = {}
    openclaw = meta.get("openclaw", {}) if isinstance(meta, dict) else {}
    requires = openclaw.get("requires", {})

    if openclaw.get("always") is True:
        return True

    if os_filter and "os" in openclaw:
        allowed_os = openclaw["os"]
        if allowed_os and os.name not in ("nt", "posix"):
            return False
        import platform
        sys_os = "win32" if os.name == "nt" else "darwin" if platform.system() == "Darwin" else "linux"
        if allowed_os and sys_os not in allowed_os:
            return False

    if requires.get("bins") and not _check_bins(requires["bins"]):
        return False
    if requires.get("env") and not _check_env(requires["env"]):
        return False
    if requires.get("config") and not _check_config(requires["config"], config):
        return False
    if requires.get("anyBins"):
        if not any(shutil.which(b) for b in requires["anyBins"]):
            return False

    return True


class Skill:
    """Representa uma skill carregada."""

    def __init__(
        self,
        name: str,
        description: str,
        instructions: str,
        location: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.description = description
        self.instructions = instructions
        self.location = location
        self.metadata = metadata or {}


class SkillsLoader:
    """
    Carrega skills de workspace, managed e bundled.
    Precedência: workspace > managed > bundled.
    """

    def __init__(
        self,
        workspace_dir: Optional[Path] = None,
        config: Optional[Dict[str, Any]] = None,
        extra_dirs: Optional[List[Path]] = None,
    ):
        self.config = config or {}
        self.workspace_dir = workspace_dir or Path.cwd()
        self.managed_dir = Path.home() / ".liteclaw" / "skills"
        self.bundled_dir = Path(__file__).resolve().parent / "bundled_skills"
        self.extra_dirs = extra_dirs or []
        self._entries_config = self.config.get("skills", {}).get("entries", {})

    def _load_skill_dir(self, skill_path: Path) -> Optional[Skill]:
        """Carrega uma skill de um diretório (deve conter SKILL.md)."""
        skill_file = skill_path / "SKILL.md"
        if not skill_file.exists():
            return None

        content = skill_file.read_text(encoding="utf-8", errors="replace")
        metadata, body = _parse_frontmatter(content)

        name = metadata.get("name") or skill_path.name
        description = metadata.get("description", "").strip()

        if not _is_skill_eligible(metadata, self.config):
            return None

        entry_cfg = self._entries_config.get(name, {})
        if isinstance(entry_cfg, dict) and entry_cfg.get("enabled") is False:
            return None

        return Skill(
            name=name,
            description=description,
            instructions=body,
            location=str(skill_path),
            metadata=metadata,
        )

    def _scan_dir(self, base: Path) -> Dict[str, Skill]:
        """Escaneia um diretório por subpastas com SKILL.md."""
        result: Dict[str, Skill] = {}
        if not base.exists():
            return result
        for item in base.iterdir():
            if item.is_dir():
                skill = self._load_skill_dir(item)
                if skill:
                    result[skill.name] = skill
        return result

    def load(self) -> List[Skill]:
        """
        Carrega todas as skills elegíveis.
        Precedência: workspace > managed > bundled > extra.
        Em conflito de nome, o primeiro vence.
        """
        seen: Dict[str, Skill] = {}

        # Ordem: bundled (menor prec), managed, workspace (maior prec), extra
        sources = [
            ("extra", d) for d in self.extra_dirs
        ] + [
            ("bundled", self.bundled_dir),
            ("managed", self.managed_dir),
            ("workspace", self.workspace_dir / "skills"),
        ]

        for _label, base in sources:
            if not isinstance(base, Path):
                base = Path(base)
            for name, skill in self._scan_dir(base).items():
                if name not in seen:
                    seen[name] = skill

        return list(seen.values())

    @staticmethod
    def format_for_prompt(skills: List[Skill]) -> str:
        """
        Formata a lista de skills em XML para injeção no system prompt.
        Formato compacto compatível com AgentSkills.
        """
        if not skills:
            return ""

        parts = ['<skills>']
        for s in skills:
            name_esc = (
                str(s.name)
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&apos;")
            )
            desc_esc = (
                str(s.description)
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&apos;")
            )
            loc_esc = (
                str(s.location)
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&apos;")
            )
            parts.append(f'  <skill name="{name_esc}" description="{desc_esc}" location="{loc_esc}" />')
        parts.append("</skills>")
        return "\n".join(parts)
