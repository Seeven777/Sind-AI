import getpass
import json
import sys
from pathlib import Path

try:
    import keyring
except Exception:
    print("Pacote keyring não encontrado. Execute install.bat.")
    raise SystemExit(1)

BASE = Path(__file__).resolve().parent
DATA = Path.home() / "JarvisData" / "wordpress"
DATA.mkdir(parents=True, exist_ok=True)
PROFILES = DATA / "profiles.json"

try:
    data = json.loads(PROFILES.read_text(encoding="utf-8")) if PROFILES.exists() else {"profiles":{}}
except Exception:
    data = {"profiles":{}}

print("=== Configurar WordPress para o Jarvis ===")
print("Use uma Application Password do WordPress. Não use sua senha principal.\n")

name = input("Nome do perfil [default]: ").strip() or "default"
site = input("URL HTTPS do site (ex: https://site.com.br): ").strip().rstrip("/")
username = input("Usuário WordPress: ").strip()
app_password = getpass.getpass("Application Password: ").strip()

if not site.startswith("https://"):
    print("ERRO: apenas HTTPS é aceito.")
    raise SystemExit(1)

if not username or not app_password:
    print("ERRO: usuário e Application Password são obrigatórios.")
    raise SystemExit(1)

data.setdefault("profiles", {})[name] = {
    "site_url": site,
    "username": username,
}
PROFILES.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
keyring.set_password("JarvisWordPress", name, app_password)

print(f"\nPerfil '{name}' salvo.")
print("A senha de aplicação foi armazenada no gerenciador de credenciais do sistema via keyring.")
