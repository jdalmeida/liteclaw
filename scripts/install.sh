#!/bin/bash
# @author João Gabriel de Almeida
python3 -m venv .venv && . .venv/bin/activate && pip install -e . && echo "✓ Instalação concluída. Ative com: source .venv/bin/activate"
