import getpass
from pathlib import Path

from connectors.gateway import ConnectorGateway

DB=Path.home()/"JarvisData"/"connectors"/"connectors.db"
gateway=ConnectorGateway(DB)

print("=== Configurar integração profissional ===\n")
print("Apenas HTTPS. O connector será criado DESABILITADO por padrão.")
print("Segredos são armazenados no keyring do sistema.\n")

name=input("Nome do serviço: ").strip()
base=input("URL-base HTTPS (ex: https://api.exemplo.com/v1/): ").strip()
print("\nAutenticação:")
print("  1. nenhuma")
print("  2. Bearer token")
print("  3. API key em header")
print("  4. Basic Auth")
choice=input("Opção [1]: ").strip() or "1"

auth_type={"1":"none","2":"bearer","3":"api_key_header","4":"basic"}.get(choice)
if not auth_type:
    raise SystemExit("Opção inválida.")

auth_config={}
secret_key=None
secret_value=None
if auth_type=="bearer":
    secret_key="token"
    secret_value=getpass.getpass("Bearer token: ").strip()
elif auth_type=="api_key_header":
    auth_config["header"]=input("Nome do header [X-API-Key]: ").strip() or "X-API-Key"
    secret_key="api_key"
    secret_value=getpass.getpass("API key: ").strip()
elif auth_type=="basic":
    auth_config["username"]=input("Usuário Basic Auth: ").strip()
    secret_key="password"
    secret_value=getpass.getpass("Senha Basic Auth: ").strip()

result=gateway.create(
    name=name,
    base_url=base,
    auth_type=auth_type,
    auth_config=auth_config,
    description="Configurado manualmente pelo usuário.",
    enabled=False,
)
if not result.get("ok"):
    existing=gateway.get(name=name)
    if not existing.get("ok"):
        raise SystemExit(result.get("error"))
    profile=existing["data"]
    gateway.update(profile["id"],base_url=base,auth_type=auth_type,auth_config=auth_config,status="disabled")
    connector_id=profile["id"]
    print("Connector existente atualizado e desabilitado.")
else:
    connector_id=result["data"]["id"]

if secret_key and secret_value:
    gateway.secret_set(connector_id,secret_key,secret_value)

print(f"\nConnector #{connector_id} configurado.")
print("Estado: DESABILITADO")
print("Use o Jarvis para cadastrar endpoints, revisar preview e só então habilitar o connector.")
print(f"Banco local: {DB}")
