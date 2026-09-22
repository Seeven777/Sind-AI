import json
import shutil
import socket
import sys
from pathlib import Path

from core.ollama_client import OllamaClient
from hardware.profiler import HardwareProfiler
from institutional.services import InstitutionalServices
from public_data.engine import PublicDataEngine


BASE=Path(__file__).resolve().parent
CFG=json.loads((BASE/"data"/"config.json").read_text(encoding="utf-8"))

def line(label,value,ok=True):
    print(f"[{'OK' if ok else 'ATENÇÃO'}] {label}: {value}")

def main():
    print("=== Jarvis Personal GPT — Doctor ===\n")

    line("Python",sys.version.split()[0])
    hw=HardwareProfiler().profile(refresh=True)
    line("Perfil de hardware",f"{hw.get('tier')} | RAM {hw.get('ram_gb')} GB | threads {hw.get('cpu_threads')}")
    if hw.get("gpus"):
        line("GPU(s)",", ".join(x.get("name","?") for x in hw["gpus"]))
    else:
        line("GPU","nenhuma detectada / integrada não identificada",False)

    ollama_cli=shutil.which("ollama")
    line("Ollama CLI",ollama_cli or "não encontrado",bool(ollama_cli))

    client=OllamaClient(
        CFG["ollama_url"],CFG["model"],CFG.get("num_ctx",4096),CFG.get("temperature",0.1)
    )
    models=client.list_models()
    line("Modelos Ollama",", ".join(models) if models else "nenhum detectado",bool(models))

    fast=CFG.get("fast_model","qwen3:1.7b")
    reason=CFG.get("reasoning_model","qwen3:4b")
    line("FAST configurado",fast,client.has_model(fast))
    line("REASON configurado",reason,client.has_model(reason))

    services=InstitutionalServices(BASE/"data"/"institutional_services.json")
    line("Serviços SindPetshop-SP",services.stats()["services"])

    pd=PublicDataEngine(BASE/"public_data"/"registry.json",BASE/"data"/"_doctor_public_proposals.json")
    stats=pd.stats()
    line("Fontes públicas",f"{stats.get('sources')} ({stats.get('official')} oficiais)")

    ui_files=["ui/web/index.html","ui/web/styles.css","ui/web/app.js"]
    for rel in ui_files:
        line(rel,"presente",(BASE/rel).exists())

    try:
        socket.create_connection(("127.0.0.1",11434),timeout=1.5).close()
        line("Ollama local","respondendo")
    except Exception:
        line("Ollama local","não respondeu em 127.0.0.1:11434",False)

    print("\nRecomendação do hardware:")
    print(json.dumps(hw.get("recommended",{}),ensure_ascii=False,indent=2))
    print("\nDoctor concluído. Itens ATENÇÃO não significam necessariamente falha; alguns recursos são opcionais.")


if __name__=="__main__":
    main()
