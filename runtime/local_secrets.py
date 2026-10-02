"""Local secret loader for Jarvis.

Secrets are kept outside Git under %USERPROFILE%/JarvisData/secrets.
Only variables that are not already present in the environment are populated.
"""
from __future__ import annotations

import os
from pathlib import Path


def _secret_root() -> Path:
    home = Path(os.environ.get("USERPROFILE") or Path.home())
    return home / "JarvisData" / "secrets"


def load_local_secrets() -> dict[str, bool]:
    loaded = {"elevenlabs": False}
    existing = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if existing and existing != "__JARVIS_ELEVENLABS_NOT_CONFIGURED__":
        loaded["elevenlabs"] = True
        return loaded

    key_path = _secret_root() / "elevenlabs_api_key.txt"
    try:
        key = key_path.read_text(encoding="utf-8").strip()
    except OSError:
        key = ""
    if key:
        os.environ["ELEVENLABS_API_KEY"] = key
        loaded["elevenlabs"] = True
    else:
        # Habitat checks only whether the environment variable is truthy before
        # selecting the ElevenLabs path. A sentinel prevents the unwanted native
        # TTS fallback; the helper recognizes it and returns a clear setup error.
        os.environ["ELEVENLABS_API_KEY"] = "__JARVIS_ELEVENLABS_NOT_CONFIGURED__"
    return loaded
