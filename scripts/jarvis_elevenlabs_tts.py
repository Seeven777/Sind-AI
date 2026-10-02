"""Generate one ElevenLabs speech file without exposing credentials to the UI."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import requests


DEFAULT_VOICE_ID = "2CECaLAGTS5NRGxgbcxr"
DEFAULT_MODEL_ID = "eleven_multilingual_v2"


def emit(**payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def load_api_key() -> str:
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if key and key != "__JARVIS_ELEVENLABS_NOT_CONFIGURED__":
        return key
    home = Path(os.environ.get("USERPROFILE") or Path.home())
    path = home / "JarvisData" / "secrets" / "elevenlabs_api_key.txt"
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def main() -> int:
    try:
        request = json.loads(sys.stdin.read() or "{}")
        text = str(request.get("text") or "").strip()
        voice_id = str(request.get("voice_id") or DEFAULT_VOICE_ID).strip()
        model_id = str(request.get("model_id") or DEFAULT_MODEL_ID).strip()
        api_key = load_api_key()
        if not api_key:
            raise RuntimeError(
                "Chave ElevenLabs não configurada. Execute Configurar-Voz-ElevenLabs.cmd."
            )
        if not text or not voice_id:
            raise RuntimeError("Texto ou voice_id ausente")

        response = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            params={"output_format": "mp3_44100_128"},
            headers={
                "xi-api-key": api_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
            json={
                "text": text[:4500],
                "model_id": model_id,
                "voice_settings": {
                    "stability": 0.46,
                    "similarity_boost": 0.86,
                    "style": 0.24,
                    "use_speaker_boost": True,
                    "speed": 1.0,
                },
            },
            timeout=90,
        )
        if not response.ok:
            content_type = response.headers.get("content-type", "")
            detail = response.text[:600] if "text" in content_type or "json" in content_type else ""
            raise RuntimeError(f"ElevenLabs HTTP {response.status_code}: {detail}")

        target = tempfile.NamedTemporaryFile(prefix="jarvis-voice-", suffix=".mp3", delete=False)
        with target:
            target.write(response.content)
        emit(ok=True, path=target.name, provider="elevenlabs", voice_id=voice_id)
        return 0
    except Exception as exc:
        emit(ok=False, error=str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
