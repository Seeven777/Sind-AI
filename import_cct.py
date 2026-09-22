from pathlib import Path
from knowledge.base import KnowledgeBase
from document_intelligence.engine import DocumentIntelligence
from institutional_knowledge.engine import InstitutionalKnowledge

home=Path.home();data=home/'JarvisData'
path=input('Arquivo da CCT (PDF/DOCX/TXT): ').strip().strip('"')
title=input('Título da CCT [nome do arquivo]: ').strip() or None
category=input('Categoria/segmento [opcional]: ').strip()
territory=input('Território/cidade [opcional]: ').strip()
base_date=input('Data-base [opcional]: ').strip()
kb=KnowledgeBase(data/'knowledge'/'knowledge.db',data/'knowledge'/'storage')
docs=DocumentIntelligence(allowed_root=home)
ik=InstitutionalKnowledge(data/'knowledge'/'institutional.db',kb,docs,home/'JarvisWorkspace')
r=ik.execute('import_file',path=path,title=title,collection='cct',category=category,territory=territory,base_date=base_date)
print(r)
