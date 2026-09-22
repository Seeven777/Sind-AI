from pathlib import Path
from knowledge.base import KnowledgeBase
from document_intelligence.engine import DocumentIntelligence
from institutional_knowledge.engine import InstitutionalKnowledge

home=Path.home();data=home/'JarvisData'
folder=input('Pasta a indexar: ').strip().strip('"')
collection=input('Nome da coleção [institutional]: ').strip() or 'institutional'
kb=KnowledgeBase(data/'knowledge'/'knowledge.db',data/'knowledge'/'storage')
docs=DocumentIntelligence(allowed_root=home)
ik=InstitutionalKnowledge(data/'knowledge'/'institutional.db',kb,docs,home/'JarvisWorkspace')
r=ik.execute('import_folder',folder=folder,collection=collection,recursive=True,limit=2000)
print(r)
