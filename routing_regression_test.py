import json
from pathlib import Path

import core.agent as agent_module
from core.agent import JarvisAgent

BASE = Path(__file__).resolve().parent
config = json.loads((BASE / "data" / "config.json").read_text(encoding="utf-8"))
agent = JarvisAgent(config, base_dir=BASE)

def forbidden_llm(*args, **kwargs):
    raise AssertionError("REGRESSÃO: comando determinístico caiu no Ollama.")

agent.ollama.chat = forbidden_llm
agent_module.open_url = lambda url: {"ok": True, "url": url}

cases = [
    "Abra o Google e pesquise sobre NR-1",
    "Abra o Google e pesquise NR-1.",
    "Pesquise NR-1 no Google",
    "Abra o YouTube e pesquise NR-1",
    "Olá",
    "Procure ações para criar uma automação diária.",
    "Procure workflows para monitorar um site.",
    "Mostre os workflows relacionados ao assistente da equipe.",
    "Mostre as ações relacionadas à fila de aprovações.",
    "Mostre as ações disponíveis para configurar uma integração profissional por API.",
    "Mostre as ações disponíveis para administrar usuários e permissões do assistente da equipe.",
    "Mostre os workflows relacionados a lacunas de conhecimento e qualidade do assistente da equipe.",
]

for case in cases:
    result = agent.run(case)
    if not isinstance(result, str) or not result.strip():
        raise AssertionError(f"Resposta vazia para: {case}")
    print("[OK]", case)
    print("    ", result[:500].replace("\n", " | "))

print("\nRouting 0.9.1 validado: os comandos acima não chamaram o modelo local.")
