import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
p=ROOT/'data'/'config.json';d=json.loads(p.read_text(encoding='utf-8'))
d['semantic_memory_enabled']=True
p.write_text(json.dumps(d,indent=2,ensure_ascii=False),encoding='utf-8')
print('Memória semântica habilitada no config desta release.')
print('Modelo:',d.get('embedding_model','nomic-embed-text-v2-moe'))
