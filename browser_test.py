import tempfile
from pathlib import Path

from browser_agent.engine import BrowserAgent

root = Path.home() / "JarvisData" / "browser_test"
downloads = Path.home() / "JarvisWorkspace" / "JarvisDownloads"
agent = BrowserAgent(root, downloads)

print("Teste do Browser Agent usando Edge/Chrome instalado.\n")
try:
    print("[1] Iniciando...")
    print(agent.start())

    print("[2] Abrindo example.com...")
    print(agent.goto("https://example.com"))

    print("[3] Título:")
    print(agent.title())

    print("[4] Texto:")
    result = agent.text(max_chars=800)
    print(result.get("text","")[:800])

    print("[5] Links:")
    print(agent.links(limit=10))

    print("\n[OK] Browser Agent respondeu.")
finally:
    try:
        agent.stop()
    except Exception:
        pass
