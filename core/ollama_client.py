import json
import socket
import time
import urllib.error
import urllib.parse
import urllib.request


class OllamaClient:
    def __init__(self, url, model, num_ctx=4096, temperature=0.1):
        self.url = url
        self.model = model
        self.num_ctx = num_ctx
        self.temperature = temperature
        self._models_cache = (0.0, [])

    def _root_url(self):
        parsed = urllib.parse.urlsplit(self.url)
        return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, "", "", "")).rstrip("/")

    def chat(self, messages, tools=None, timeout=45, model=None, num_ctx=None, temperature=None):
        selected_model = model or self.model
        payload = {
            "model": selected_model,
            "messages": messages,
            "stream": False,
            "think": False,
            "options": {
                "temperature": self.temperature if temperature is None else temperature,
                "num_ctx": int(num_ctx or self.num_ctx),
            },
        }
        if tools:
            payload["tools"] = tools

        req = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=float(timeout)) as response:
                data = json.loads(response.read().decode("utf-8"))
                data["_jarvis_model"] = selected_model
                return data
        except (socket.timeout, TimeoutError) as exc:
            raise RuntimeError(f"O modelo local {selected_model} ultrapassou {int(timeout)}s nesta etapa.") from exc
        except urllib.error.HTTPError as exc:
            try:
                body = exc.read().decode("utf-8", errors="replace")
            except Exception:
                body = ""
            raise RuntimeError(f"Ollama retornou HTTP {exc.code} para {selected_model}: {body[:500]}") from exc
        except urllib.error.URLError as exc:
            if isinstance(getattr(exc, "reason", None), socket.timeout):
                raise RuntimeError(f"O modelo local {selected_model} ultrapassou {int(timeout)}s nesta etapa.") from exc
            raise RuntimeError("Não consegui conectar ao Ollama. Confirme que o aplicativo Ollama está aberto.") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError("O Ollama retornou uma resposta inválida.") from exc

    def list_models(self, max_age_seconds=20):
        now = time.monotonic()
        cached_at, cached = self._models_cache
        if cached and now - cached_at <= max_age_seconds:
            return list(cached)
        req = urllib.request.Request(
            self._root_url() + "/api/tags",
            headers={"Accept": "application/json"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode("utf-8"))
            models = []
            for item in data.get("models", []):
                name = item.get("name") or item.get("model")
                if name:
                    models.append(str(name))
            self._models_cache = (now, models)
            return models
        except Exception:
            return []

    def has_model(self, model):
        wanted = str(model).strip()
        models = self.list_models()
        if wanted in models:
            return True
        if ":" not in wanted and wanted + ":latest" in models:
            return True
        return False
