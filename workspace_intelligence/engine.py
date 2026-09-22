import json
import os
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path


class WorkspaceIntelligence:
    def __init__(self, root):
        self.root=Path(root).resolve(); self.root.mkdir(parents=True,exist_ok=True)

    def _safe(self,path=None):
        p=Path(path).expanduser().resolve() if path else self.root
        if self.root not in p.parents and p!=self.root: raise PermissionError('Fora do workspace permitido.')
        return p

    def inventory(self,path=None,limit=5000):
        try:
            root=self._safe(path); items=[]
            for p in root.rglob('*'):
                if not p.is_file():continue
                st=p.stat(); items.append({'path':str(p),'relative':str(p.relative_to(root)),'name':p.name,'ext':p.suffix.lower(),'size':st.st_size,'mtime':st.st_mtime})
                if len(items)>=int(limit):break
            return {'ok':True,'root':str(root),'items':items,'count':len(items)}
        except Exception as exc:return {'ok':False,'error':str(exc)}

    def summary(self,path=None):
        r=self.inventory(path)
        if not r.get('ok'):return r
        ext=Counter(x['ext'] or '(none)' for x in r['items']); total=sum(x['size'] for x in r['items'])
        return {'ok':True,'files':len(r['items']),'bytes':total,'extensions':dict(ext.most_common()),'root':r['root']}

    def recent(self,path=None,hours=24,limit=100):
        r=self.inventory(path)
        if not r.get('ok'):return r
        cutoff=datetime.now().timestamp()-float(hours)*3600
        items=[x for x in r['items'] if x['mtime']>=cutoff]
        items.sort(key=lambda x:-x['mtime'])
        for x in items:x['modified']=datetime.fromtimestamp(x['mtime']).isoformat(timespec='seconds')
        return {'ok':True,'items':items[:int(limit)],'count':len(items)}

    def by_extension(self,path=None):
        r=self.inventory(path)
        if not r.get('ok'):return r
        groups=defaultdict(list)
        for x in r['items']:groups[x['ext'] or '(none)'].append(x['path'])
        return {'ok':True,'groups':dict(groups),'counts':{k:len(v) for k,v in groups.items()}}

    def project_candidates(self,path=None):
        root=self._safe(path); markers={'package.json','pyproject.toml','requirements.txt','.git','*.sln','*.csproj','composer.json','wp-config.php'}; items=[]
        for d in [root]+[p for p in root.iterdir() if p.is_dir()]:
            found=[]
            names={p.name for p in d.iterdir()} if d.exists() else set()
            for m in markers:
                if '*' in m:
                    if list(d.glob(m)):found.append(m)
                elif m in names:found.append(m)
            if found:items.append({'path':str(d),'markers':found})
        return {'ok':True,'items':items,'count':len(items)}

    def empty_dirs(self,path=None,limit=200):
        root=self._safe(path); items=[]
        for d in root.rglob('*'):
            if d.is_dir():
                try:
                    if not any(d.iterdir()):items.append(str(d))
                except Exception:pass
            if len(items)>=int(limit):break
        return {'ok':True,'items':items,'count':len(items)}

    def filename_search(self,query,path=None,limit=200):
        r=self.inventory(path)
        if not r.get('ok'):return r
        q=str(query).lower(); items=[x for x in r['items'] if q in x['name'].lower()]
        return {'ok':True,'items':items[:int(limit)],'count':len(items)}

    def size_buckets(self,path=None):
        r=self.inventory(path)
        if not r.get('ok'):return r
        b={'<100KB':0,'100KB-1MB':0,'1-10MB':0,'10-100MB':0,'>100MB':0}
        for x in r['items']:
            s=x['size']
            if s<100_000:b['<100KB']+=1
            elif s<1_000_000:b['100KB-1MB']+=1
            elif s<10_000_000:b['1-10MB']+=1
            elif s<100_000_000:b['10-100MB']+=1
            else:b['>100MB']+=1
        return {'ok':True,'buckets':b}

    def disk_space(self):
        u=shutil.disk_usage(self.root)
        return {'ok':True,'total':u.total,'used':u.used,'free':u.free,'free_percent':round(u.free/max(1,u.total)*100,2)}

    def tree(self,path=None,depth=3,limit=500):
        root=self._safe(path); items=[]; base_parts=len(root.parts)
        for p in root.rglob('*'):
            d=len(p.parts)-base_parts
            if d>int(depth):continue
            items.append({'path':str(p.relative_to(root)),'type':'dir' if p.is_dir() else 'file','depth':d})
            if len(items)>=int(limit):break
        return {'ok':True,'root':str(root),'items':items,'count':len(items)}

    def manifest(self,path=None,out_name='workspace_manifest.json'):
        r=self.inventory(path)
        if not r.get('ok'):return r
        out=self.root/out_name
        out.write_text(json.dumps(r,indent=2,ensure_ascii=False),encoding='utf-8')
        return {'ok':True,'path':str(out),'files':r['count']}

    def execute(self,operation,**p):
        path=p.get('path')
        if operation=='inventory':return self.inventory(path,p.get('limit',5000))
        if operation=='summary':return self.summary(path)
        if operation=='recent':return self.recent(path,p.get('hours',24),p.get('limit',100))
        if operation=='by_extension':return self.by_extension(path)
        if operation=='project_candidates':return self.project_candidates(path)
        if operation=='empty_dirs':return self.empty_dirs(path,p.get('limit',200))
        if operation=='filename_search':return self.filename_search(p.get('query',''),path,p.get('limit',200))
        if operation=='size_buckets':return self.size_buckets(path)
        if operation=='disk_space':return self.disk_space()
        if operation=='tree':return self.tree(path,p.get('depth',3),p.get('limit',500))
        if operation=='manifest':return self.manifest(path,p.get('out_name','workspace_manifest.json'))
        return {'ok':False,'error':f'Operação de workspace desconhecida: {operation}'}
