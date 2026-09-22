import getpass
from pathlib import Path

from team_assistant.engine import TeamAssistantEngine

DB = Path.home() / 'JarvisData' / 'team' / 'team.db'
team = TeamAssistantEngine(DB)

print('=== Configurar Sind Assist / Team Portal ===\n')
roles = team.role_list(limit=100).get('items', [])
if not roles:
    created = team.role_create('admin', 'Administrador local do Sind Assist')
    role_id = created.get('data', {}).get('id') or created.get('id')
    print('Role admin criada.')
else:
    print('Roles existentes:')
    for r in roles:
        print(f"  {r['id']}: {r['name']}")
    raw = input('ID da role para o novo usuário [admin/primeira]: ').strip()
    role_id = int(raw) if raw else int(roles[0]['id'])

username = input('Usuário: ').strip().lower()
display = input('Nome de exibição: ').strip() or username
password = getpass.getpass('Senha local: ').strip()
if not username or not password:
    raise SystemExit('Usuário e senha são obrigatórios.')

existing = team.user_by_username(username)
if existing:
    team.password_set(existing['id'], password)
    team.user_update(existing['id'], display_name=display, role_id=role_id, status='active')
    user_id = existing['id']
    print('Usuário atualizado.')
else:
    result = team.user_create(username, display, role_id=role_id, password=password)
    if not result.get('ok'):
        raise SystemExit(result.get('error'))
    user_id = result['data']['id']
    print('Usuário criado.')

host = input('Host do portal [127.0.0.1]: ').strip() or '127.0.0.1'
port = input('Porta [8765]: ').strip() or '8765'
team.setting_set('portal_host', host)
team.setting_set('portal_port', port)

print('\nConfiguração concluída.')
print(f'Banco: {DB}')
print('Execute run_team_portal.bat para iniciar o portal.')
if host == '0.0.0.0':
    print('ATENÇÃO: 0.0.0.0 expõe o portal na rede local. Use firewall e senha forte.')
