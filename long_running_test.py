import json
import urllib.request
from pathlib import Path
from unittest.mock import patch

from core.ollama_client import OllamaClient


class FakeResponse:
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return False
    def read(self):
        return json.dumps({"message":{"role":"assistant","content":"ok"}}).encode("utf-8")


def check(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name}: {detail}")
    print("[OK]", name)


def main():
    base = Path(__file__).resolve().parent
    cfg = json.loads((base/"data"/"config.json").read_text(encoding="utf-8"))

    check("Agent LLM timeout disabled", cfg.get("agent_llm_timeout_seconds") == 0, cfg)
    check("Agent total timeout disabled", cfg.get("agent_total_timeout_seconds") == 0, cfg)
    check("Fast model timeout disabled", cfg.get("fast_model_timeout_seconds") == 0, cfg)
    check("Research LLM timeout disabled", cfg.get("research_llm_timeout_seconds") == 0, cfg)

    client = OllamaClient("http://127.0.0.1:11434/api/chat", "qwen3:4b")
    calls = []

    def fake_urlopen(req, *args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})
        return FakeResponse()

    with patch.object(urllib.request, "urlopen", fake_urlopen):
        result = client.chat([{"role":"user","content":"teste"}], timeout=0)

    check("Unlimited call returns normally", result["message"]["content"] == "ok", result)
    check("No socket deadline passed", "timeout" not in calls[0]["kwargs"], calls)

    agent_source = (base/"core"/"agent.py").read_text(encoding="utf-8")
    check("Unlimited total budget branch present", "if total_budget > 0 and elapsed >= total_budget" in agent_source)
    check("Model progress status present", "Pensando com {model_name}" in agent_source)

    habitat_source = (base/"ui"/"habitat.py").read_text(encoding="utf-8")
    check("Heartbeat timer present", "_emit_task_heartbeat" in habitat_source)
    check("Elapsed time formatter present", "_format_elapsed" in habitat_source)

    print("\\nLong-running runtime test concluído.")


if __name__ == "__main__":
    main()
