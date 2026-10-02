"""Generate one ElevenLabs speech file without exposing credentials to the UI."""

from __future__ import annotations

import json
import os
import sys
import tempfile

import requests


def emit(**payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def main() -> int:
    try:
        request = json.loads(sys.stdin.read() or "{}")
        text = str(request.get("text") or "").strip()
        voice_id = str(request.get("voice_id") or "").strip()
        model_id = str(request.get("model_id") or "eleven_multilingual_v2")
        api_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("ELEVENLABS_API_KEY não configurada")
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
                    "stability": 0.55,
                    "similarity_boost": 0.78,
                    "style": 0.18,
                    "use_speaker_boost": True,
                    "speed": 1.04,
                },
            },
            timeout=90,
        )
        if not response.ok:
            detail = response.text[:600] if "text" in response.headers.get("content-type", "") else ""
            raise RuntimeError(f"ElevenLabs HTTP {response.status_code}: {detail}")

        target = tempfile.NamedTemporaryFile(prefix="jarvis-voice-", suffix=".mp3", delete=False)
        with target:
            target.write(response.content)
        emit(ok=True, path=target.name, provider="elevenlabs")
        return 0
    except Exception as exc:
        emit(ok=False, error=str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
