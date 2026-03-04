"""
 * @author João Gabriel de Almeida
 """

"""Registro e definição de tools para o LiteClaw."""

import json
import inspect
from typing import Any, Callable, Dict, List, Optional, get_type_hints


def _python_type_to_json_schema(annotation: type) -> Dict[str, Any]:
    """Converte tipo Python para JSON Schema."""
    type_map = {
        str: {"type": "string"},
        int: {"type": "integer"},
        float: {"type": "number"},
        bool: {"type": "boolean"},
        list: {"type": "array"},
        dict: {"type": "object"},
    }
    return type_map.get(annotation, {"type": "string"})


def tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> Callable:
    """
    Decorator para registrar uma função como tool.

    Args:
        name: Nome da tool (default: nome da função)
        description: Descrição da tool (default: docstring da função)

    Example:
        @tool(description="Retorna o clima de uma localização")
        def get_weather(location: str) -> dict:
            return {"temperature": 25, "condition": "Sunny"}
    """

    def decorator(func: Callable) -> Callable:
        tool_name = name or func.__name__
        tool_desc = description or (func.__doc__ or "").strip().split("\n")[0]

        sig = inspect.signature(func)
        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue
            annotation = param.annotation if param.annotation != inspect.Parameter.empty else str
            properties[param_name] = {
                "type": _python_type_to_json_schema(annotation)["type"],
                "description": f"Parâmetro {param_name}",
            }
            if param.default == inspect.Parameter.empty:
                required.append(param_name)

        func._liteclaw_tool = {
            "name": tool_name,
            "description": tool_desc,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
            "callable": func,
        }
        return func

    return decorator


class ToolRegistry:
    """Registro de tools disponíveis para o modelo."""

    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}

    def register(self, func: Callable) -> None:
        """Registra uma função decorada com @tool."""
        if hasattr(func, "_liteclaw_tool"):
            tool_def = func._liteclaw_tool.copy()
            tool_def.pop("callable", None)
            self._tools[tool_def["name"]] = {
                **tool_def,
                "callable": func,
            }
        else:
            raise ValueError(
                f"A função {func.__name__} deve ser decorada com @tool"
            )

    def register_function(
        self,
        name: str,
        func: Callable,
        description: str = "",
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Registra uma função com definição manual."""
        params = parameters or {"type": "object", "properties": {}, "required": []}
        self._tools[name] = {
            "name": name,
            "description": description or f"Tool {name}",
            "parameters": params,
            "callable": func,
        }

    def get_gemini_format(self) -> List[Dict[str, Any]]:
        """Retorna as tools no formato da API Gemini."""
        return [
            {
                "functionDeclarations": [
                    {
                        "name": t["name"],
                        "description": t["description"],
                        "parameters": t["parameters"],
                    }
                    for t in self._tools.values()
                ]
            }
        ]

    def call(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Executa uma tool pelo nome."""
        if name not in self._tools:
            return {"error": f"Tool '{name}' não encontrada"}

        tool_def = self._tools[name]
        func = tool_def["callable"]

        try:
            result = func(**arguments)
            if isinstance(result, (dict, list)):
                return result
            return {"result": str(result)}
        except Exception as e:
            return {"error": str(e)}

    def __contains__(self, name: str) -> bool:
        return name in self._tools
