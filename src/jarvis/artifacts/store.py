import hashlib,re
from pathlib import Path
def safe_name(v): return re.sub(r'[^a-zA-Z0-9._-]+','-',v.strip()).strip('-') or 'artifact'
class ArtifactStore:
    def __init__(self,root,repository): self.root=Path(root); self.repository=repository
    def write_text(self,*,task_id,agent_id,name,content,artifact_type='text/markdown',metadata=None):
        folder=self.root/task_id; folder.mkdir(parents=True,exist_ok=True); filename=safe_name(name); filename += '' if '.' in filename else '.md'; path=folder/filename; path.write_text(content,encoding='utf-8'); checksum=hashlib.sha256(path.read_bytes()).hexdigest(); rel=str(path.relative_to(self.root.parent)); aid=self.repository.add(task_id=task_id,agent_id=agent_id,artifact_type=artifact_type,name=filename,relative_path=rel,checksum=checksum,metadata=metadata); return {'artifact_id':aid,'name':filename,'path':str(path),'checksum':checksum,'content':content}
