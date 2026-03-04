"""
 * @author João Gabriel de Almeida
 """

"""LiteClaw - Wrapper Python para LiteRT-LM com suporte a tools."""

from liteclaw.client import LiteClawClient
from liteclaw.tools import tool, ToolRegistry

__all__ = ["LiteClawClient", "tool", "ToolRegistry"]
