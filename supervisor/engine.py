import json
import os
import shutil
import socket
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests


class RuntimeSupervisor:
    def __init__(self, config, persistent_root, workspace, tasks=None, diagnostics=None, browser=None, ollama_url=None, base_dir=None):
        self.config=dict(config or {})
        self.persistent_root=Path(persistent_root)
        self.workspace=Path(workspace)
        self.tasks=tasks
        self.diagnostics=diagnostics
        self.browser=browser
        self.ollama_url=str(ollama_url or 'http://127.0.0.1:11434/api/chat')
        self.base_dir=Path(base_dir) if base_dir else None

    def _writable(self,path):
        try:
            p=Path(path); p.mkdir(parents=True,exist_ok=True); probe=p/'.jarvis_write_test'
            probe.write_text('ok',encoding='utf-8'); probe.unlink(missing_ok=True); return True
        except Exception:return False

    def ollama_health(self):
        try:
            base=self.ollama_url.split('/api/',1)[0]
            r=requests.get(base+'/api/tags',timeout=3)
            data=r.json() if r.ok else {}
            models=[x.get('name') or x.get('model') for x in data.get('models',[])]
            target=self.config.get('model','qwen3:4b')
            return {'ok':r.ok,'status':r.status_code,'model':target,'model_available':any(str(x).startswith(target) for x in models),'models':models[:30]}
        except Exception as exc:return {'ok':False,'error':str(exc),'model':self.config.get('model','qwen3:4b')}

    def dns_health(self,host='google.com'):
        try:
            ip=socket.gethostbyname(host); return {'ok':True,'host':host,'ip':ip}
        except Exception as exc:return {'ok':False,'host':host,'error':str(exc)}

    def internet_health(self,url='https://example.com'):
        try:
            start=time.monotonic(); r=requests.get(url,timeout=5); ms=round((time.monotonic()-start)*1000,1)
            return {'ok':r.ok,'status':r.status_code,'elapsed_ms':ms,'url':r.url}
        except Exception as exc:return {'ok':False,'error':str(exc),'url':url}

    def disk_health(self):
        u=shutil.disk_usage(self.workspace)
        return {'ok':u.free>500_000_000,'total':u.total,'used':u.used,'free':u.free,'free_percent':round(u.free/max(1,u.total)*100,2)}

    def directory_health(self):
        return {'ok':self._writable(self.workspace) and self._writable(self.persistent_root),
                'workspace_writable':self._writable(self.workspace),'persistent_writable':self._writable(self.persistent_root),
                'workspace':str(self.workspace),'persistent_root':str(self.persistent_root)}

    def sqlite_health(self,path):
        try:
            p=Path(path)
            if not p.exists():return {'ok':True,'exists':False,'path':str(p),'note':'ainda não criado'}
            conn=sqlite3.connect(p); row=conn.execute('PRAGMA integrity_check').fetchone(); conn.close()
            verdict=row[0] if row else 'unknown'; return {'ok':verdict=='ok','exists':True,'path':str(p),'integrity':verdict}
        except Exception as exc:return {'ok':False,'path':str(path),'error':str(exc)}

    def catalog_health(self,path,key):
        try:
            p=Path(path); data=json.loads(p.read_text(encoding='utf-8'))
            items = data if isinstance(data, list) else data.get(key, [])
            ids=[x.get('id') for x in items]; return {'ok':bool(items) and len(ids)==len(set(ids)),'path':str(p),'count':len(items),'unique_ids':len(ids)==len(set(ids))}
        except Exception as exc:return {'ok':False,'path':str(path),'error':str(exc)}

    def browser_health(self):
        try:
            r=self.browser.status() if self.browser else {'running':False}; return {'ok':True,**r}
        except Exception as exc:return {'ok':False,'error':str(exc)}

    def stale_tasks(self):
        if not self.tasks:return {'ok':True,'items':[],'count':0}
        try:return {'ok':True,**self.tasks.stale_tasks()}
        except Exception as exc:return {'ok':False,'error':str(exc)}

    def reconcile_tasks(self):
        if not self.tasks:return {'ok':True,'interrupted':0}
        try:return self.tasks.reconcile_stale(reason='Jarvis reiniciado ou worker anterior não existe mais.')
        except Exception as exc:return {'ok':False,'error':str(exc)}

    def recent_errors(self,limit=20):
        if not self.diagnostics:return {'ok':True,'items':[]}
        items=[x for x in self.diagnostics.recent(limit=max(int(limit)*3,30)) if x.get('kind')=='error'][-int(limit):]
        return {'ok':True,'items':items,'count':len(items)}

    def budget(self):
        return {'ok':True,'llm_timeout_seconds':self.config.get('agent_llm_timeout_seconds'),
                'total_timeout_seconds':self.config.get('agent_total_timeout_seconds'),
                'max_rounds':self.config.get('agent_max_rounds'),'max_tool_calls':self.config.get('agent_max_tool_calls'),
                'context':self.config.get('num_ctx'),'model':self.config.get('model')}

    def quick_health(self):
        dirs=self.directory_health(); disk=self.disk_health(); browser=self.browser_health()
        return {'ok':dirs.get('ok') and disk.get('ok'),'directories':dirs,'disk':disk,'browser':browser,'budget':self.budget()}

    def full_health(self):
        checks={
            'ollama':self.ollama_health(), 'dns':self.dns_health(), 'internet':self.internet_health(),
            'directories':self.directory_health(), 'disk':self.disk_health(), 'browser':self.browser_health(),
            'stale_tasks':self.stale_tasks(), 'budget':self.budget(),
        }
        if self.base_dir:
            checks['actions_catalog']=self.catalog_health(self.base_dir/'actions'/'catalog.json','actions')
            checks['workflows_catalog']=self.catalog_health(self.base_dir/'workflows'/'catalog.json','workflows')
            checks['capability_catalog']=self.catalog_health(self.base_dir/'capabilities'/'catalog.json','capabilities')
        ok=all(v.get('ok',False) for k,v in checks.items() if k not in {'stale_tasks','budget'})
        return {'ok':ok,'checks':checks,'time':datetime.now().isoformat(timespec='seconds')}

    def diagnostic_bundle(self):
        return {'ok':True,'health':self.full_health(),'recent_errors':self.recent_errors(20),
                'recent_tasks':self.tasks.recent(10) if self.tasks else []}

    def execute(self,operation,**p):
        if operation=='ollama_health':return self.ollama_health()
        if operation=='dns_health':return self.dns_health(p.get('host','google.com'))
        if operation=='internet_health':return self.internet_health(p.get('url','https://example.com'))
        if operation=='disk_health':return self.disk_health()
        if operation=='directory_health':return self.directory_health()
        if operation=='browser_health':return self.browser_health()
        if operation=='stale_tasks':return self.stale_tasks()
        if operation=='reconcile_tasks':return self.reconcile_tasks()
        if operation=='recent_errors':return self.recent_errors(p.get('limit',20))
        if operation=='budget':return self.budget()
        if operation=='quick_health':return self.quick_health()
        if operation=='full_health':return self.full_health()
        if operation=='diagnostic_bundle':return self.diagnostic_bundle()
        if operation=='sqlite_health':return self.sqlite_health(p.get('path',''))
        if operation=='catalog_health':return self.catalog_health(p.get('path',''),p.get('key','items'))
        return {'ok':False,'error':f'Operação de supervisor desconhecida: {operation}'}
