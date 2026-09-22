import json
from pathlib import Path

from institutional.store import InstitutionalStore

ROOT=Path.home()/"JarvisData"
DB=ROOT/"institutional"/"institutional.db"
store=InstitutionalStore(DB)

print("=== Jarvis • Configuração Institucional ===\n")
print("Pressione Enter para deixar um campo sem alterar.\n")
fields=[
    ("organization_name","Nome da organização"),
    ("public_name","Nome público/abreviado"),
    ("website","Site institucional"),
    ("instagram","Instagram institucional"),
    ("mission","Missão/resumo institucional"),
    ("primary_audience","Público principal"),
    ("default_language","Idioma padrão"),
    ("content_tone","Tom de comunicação"),
]
existing=store.execute("profile_get").get("data",{})
for key,label in fields:
    current=existing.get(key,"")
    value=input(f"{label}" + (f" [{current}]" if current else "") + ": ").strip()
    if value:
        store.execute("profile_set",key=key,value=value)

print("\nConfiguração salva em:",DB)
print(json.dumps(store.execute("profile_get").get("data",{}),ensure_ascii=False,indent=2))
