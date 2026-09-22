import tempfile
from pathlib import Path
from public_data.engine import PublicDataEngine
BASE=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as raw:
    e=PublicDataEngine(BASE/'public_data'/'registry.json',Path(raw)/'proposals.json')
    tests=[('IBGE estados','ibge','states',{}),('Crossref','crossref','works',{'query':'artificial intelligence','rows':1}),('Dados.gov.br','dados_gov_br','datasets',{'titulo':'trabalho','limit':2})]
    for name,source,op,params in tests:
        r=e.query(source,op,params);print(f"[{'OK' if r.get('ok') else 'FALHOU'}] {name}")
        if not r.get('ok'):print(' ',r.get('error'))
    print('\nTeste online é best-effort: fontes públicas podem mudar ou aplicar rate limit.')
