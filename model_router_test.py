import json
from pathlib import Path
from core.ollama_client import OllamaClient
from cognitive.model_router import AdaptiveModelRouter

BASE = Path(__file__).resolve().parent
cfg = json.loads((BASE/"data"/"config.json").read_text(encoding="utf-8"))
client = OllamaClient(cfg["ollama_url"], cfg["model"], cfg.get("num_ctx",4096), cfg.get("temperature",0.1))
router = AdaptiveModelRouter(
    client,
    cfg.get("fast_model","qwen3:1.7b"),
    cfg.get("reasoning_model","qwen3:4b"),
    cfg.get("fast_model_timeout_seconds",18),
    cfg.get("agent_llm_timeout_seconds",40),
    cfg.get("fast_model_fallback_timeout_seconds",22),
)
print(json.dumps(router.status(), indent=2, ensure_ascii=False))
print("\nConversa curta:")
resp = router.chat(
    [{"role":"system","content":"Responda em português em uma frase."},
     {"role":"user","content":"Diga apenas: Jarvis pronto."}],
    user_text="Diga apenas: Jarvis pronto.",
    force="fast",
)
print((resp.get("message") or {}).get("content"))
print("Modelo usado:", resp.get("_jarvis_model"))
