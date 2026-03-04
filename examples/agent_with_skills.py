#!/usr/bin/env python3
"""
 * @author João Gabriel de Almeida
 """

"""
Exemplo de uso do Agent com skills e tools builtin.
"""

from liteclaw import Agent, LiteClawClient
from liteclaw.session import SessionManager
from liteclaw.skills import SkillsLoader
from liteclaw.tools_builtin import register_builtin_tools


def main():
    client = LiteClawClient(model="qwen2.5-1.5b", port=9379, auto_start=True)
    register_builtin_tools(client.tools)

    session_manager = SessionManager()
    skills_loader = SkillsLoader()

    agent = Agent(
        client=client,
        session_manager=session_manager,
        skills_loader=skills_loader,
    )

    print("LiteClaw Agent - Digite 'sair' para encerrar.\n")
    try:
        while True:
            user_input = input("Você: ").strip()
            if user_input.lower() in ("sair", "exit", "quit"):
                break
            if not user_input:
                continue
            response = agent.run(user_input)
            print(f"\nAgente: {response}\n")
    finally:
        client.stop_server()


if __name__ == "__main__":
    main()
