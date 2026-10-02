"""Configure the ElevenLabs key in the user-owned JarvisData directory."""
from __future__ import annotations

import getpass
import os
from pathlib import Path


def main() -> int:
    home = Path(os.environ.get("USERPROFILE") or Path.home())
    secret_dir = home / "JarvisData" / "secrets"
    secret_dir.mkdir(parents=True, exist_ok=True)
    target = secret_dir / "elevenlabs_api_key.txt"

    print("Configuração da voz neural do Jarvis")
    print("A chave ficará somente em JarvisData\\secrets e não deve ser enviada ao Git.")
    key = getpass.getpass("Cole sua ELEVENLABS_API_KEY e pressione Enter: ").strip()
    if not key:
        print("Nenhuma chave informada. Nada foi alterado.")
        return 1
    if len(key) < 10:
        print("A chave informada parece inválida. Nada foi alterado.")
        return 1

    target.write_text(key, encoding="utf-8")
    try:
        os.chmod(target, 0o600)
    except OSError:
        pass
    print(f"OK: chave salva em {target}")
    print("Reinicie o Jarvis. A voz configurada será 2CECaLAGTS5NRGxgbcxr.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
