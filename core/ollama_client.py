import json
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request


def sanitize_assistant_content(content):
    """
    Never expose model chain-of-thought / <think> blocks to the product UI.

    Qwen can occasionally return a closing </think> even when `think:false`
    was requested. In that case the useful answer is the text after the final
    closing tag.
    """
    s = str(content or "")
    if not s:
        return ""

    lower = s.lower()
    closing = "</think>"
    if closing in lower:
        idx = lower.rfind(closing)
        s = s[idx + len(closing):]

    s = re.sub(r"<think\b[^>]*>.*?</think>", "", s, flags=re.I | re.S)
    s = re.sub(r"</?think\b[^>]*>", "", s, flags=re.I)

    # If the model starts an unclosed think block, do not leak it.
    if re.match(r"^\s*<think\b", str(content or ""), flags=re.I) and "</think>" not in lower:
        return ""

    return s.strip()


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
            # timeout <= 0 significa execução sem deadline artificial.
            # O usuário continua podendo cancelar a tarefa pela interface.
            if timeout is None or float(timeout) <= 0:
                response_ctx = urllib.request.urlopen(req)
            else:
                response_ctx = urllib.request.urlopen(req, timeout=float(timeout))

            with response_ctx as response:
                data = json.loads(response.read().decode("utf-8"))
                message = data.get("message")
                if isinstance(message, dict) and "content" in message:
                    message["content"] = sanitize_assistant_content(message.get("content"))
                data["_jarvis_model"] = selected_model
                return data
        except (socket.timeout, TimeoutError) as exc:
            if timeout is None or float(timeout) <= 0:
                raise RuntimeError(f"A conexão com o modelo local {selected_model} foi interrompida.") from exc
            raise RuntimeError(f"O modelo local {selected_model} ultrapassou {int(timeout)}s nesta etapa.") from exc
        except urllib.error.HTTPError as exc:
            try:
                body = exc.read().decode("utf-8", errors="replace")
            except Exception:
                body = ""
            raise RuntimeError(f"Ollama retornou HTTP {exc.code} para {selected_model}: {body[:500]}") from exc
        except urllib.error.URLError as exc:
            if isinstance(getattr(exc, "reason", None), socket.timeout):
                if timeout is None or float(timeout) <= 0:
                    raise RuntimeError(f"A conexão com o modelo local {selected_model} foi interrompida.") from exc
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
