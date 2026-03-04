#!/usr/bin/env python3
"""
 * @author João Gabriel de Almeida
 """

"""
Exemplo de uso do LiteClaw com tools.

NOTA: Para tool calling, use um modelo que suporte function calling, como:
- tiny_garden (FunctionGemma-270M) - baixe com: lit pull google/functiongemma-270m-it
- Ou verifique a documentação do LiteRT-LM para modelos compatíveis.

Modelos como qwen2.5-1.5b e gemma3-1b podem não suportar tools nativamente.
"""

from liteclaw import LiteClawClient, tool


@tool(description="Retorna o clima de uma localização")
def get_weather(location: str) -> dict:
    """Simula dados de clima para uma localização."""
    return {
        "location": location,
        "temperature": 25,
        "unit": "celsius",
        "condition": "Ensolarado",
        "humidity": 65,
    }


@tool(description="Retorna o preço de uma ação pelo símbolo")
def get_stock_price(stock_symbol: str) -> dict:
    """Simula o preço de uma ação."""
    prices = {"AAPL": 178.50, "GOOGL": 141.20, "MSFT": 378.91}
    price = prices.get(stock_symbol.upper(), 100.0)
    return {
        "stock_symbol": stock_symbol,
        "price": price,
        "currency": "USD",
    }


def main():
    client = LiteClawClient(
        model="qwen2.5-1.5b",
        port=9379,
        auto_start=True,
    )

    client.tools.register(get_weather)
    client.tools.register(get_stock_price)

    print("LiteClaw - Chat com Tools")
    print("Digite 'sair' para encerrar.\n")

    try:
        while True:
            user_input = input("Você: ").strip()
            if user_input.lower() in ("sair", "exit", "quit"):
                break
            if not user_input:
                continue

            response = client.chat(user_input)
            print(f"\nModelo: {response}\n")
    finally:
        client.stop_server()


if __name__ == "__main__":
    main()
