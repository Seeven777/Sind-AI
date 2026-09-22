from pathlib import Path
from wordpress.manager import WordPressManager

profiles = Path.home() / "JarvisData" / "wordpress" / "profiles.json"
wp = WordPressManager(profiles)

items = wp.list_profiles()
print("Perfis WordPress configurados:")
print(items)

if not items.get("items"):
    print("\nNenhum perfil configurado.")
    print("Execute configure_wordpress.bat primeiro.")
    raise SystemExit(0)

for item in items["items"]:
    name = item["name"]
    print(f"\n[{name}] Descobrindo REST API...")
    print(wp.discover(item["site_url"]))
    print(f"[{name}] Verificando Application Password...")
    print(wp.execute("auth_status", profile=name))
    print(f"[{name}] Listando rascunhos/posts visíveis (sem alterar nada)...")
    print(wp.execute("list_posts", profile=name, per_page=3))
