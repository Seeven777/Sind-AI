from __future__ import annotations

import json
import re
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .base import ConnectorItem, SyncResult


_TASK_KEYS = {
    'title','titulo','título','name','nome','task','tarefa','subject','assunto',
    'description','descricao','descrição','status','state','estado','due_date','deadline',
    'date','data','start_date','end_date','priority','prioridade','completed','done','is_done',
}
_TITLE_KEYS = ('title','titulo','título','name','nome','task','tarefa','subject','assunto')
_DESC_KEYS = ('description','descricao','descrição','details','detalhes','content','conteudo','conteúdo','notes','observacoes','observações')
_STATUS_KEYS = ('status','state','estado','stage','coluna','column')
_DATE_KEYS = ('due_date','deadline','date','data','start_date','end_date','due','prazo')
_PRIORITY_KEYS = ('priority','prioridade','importance','importancia','importância')
_ID_KEYS = ('id','task_id','uuid','key')
_DONE_WORDS = {'done','completed','complete','concluido','concluído','finalizado','finalizada','feito','feita','closed','arquivado','archived'}


def _pick(record: dict, keys, default=''):
    lowered={str(k).lower():v for k,v in record.items()}
    for key in keys:
        if key in lowered and lowered[key] not in (None,''):
            return lowered[key]
    return default


def _clean(value, limit=1000):
    return ' '.join(str(value or '').split())[:limit]


def _iso(value):
    if not value:
        return None
    text=str(value).strip()
    # Preserve service timestamps; normalize simple dates to local midnight ISO-ish.
    try:
        return datetime.fromisoformat(text.replace('Z','+00:00')).isoformat()
    except Exception:
        pass
    for fmt in ('%d/%m/%Y','%Y-%m-%d','%d-%m-%Y'):
        try:
            return datetime.strptime(text,fmt).replace(tzinfo=timezone.utc).isoformat()
        except Exception:
            continue
    return None


def _walk_json(value: Any):
    if isinstance(value, dict):
        keys={str(k).lower() for k in value}
        if len(keys & _TASK_KEYS) >= 2 and any(k in keys for k in _TITLE_KEYS):
            yield value
        for child in value.values():
            yield from _walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_json(child)


class MarketingTasksConnector:
    """Read-only connector for the user's marketing task web app.

    The connector intentionally stores no password in source code. Credentials are
    protected by Jarvis' Windows DPAPI SecretStore and the authenticated browser
    session is persisted as Playwright storage state. During sync, Jarvis first
    observes JSON API responses (including Supabase REST payloads) and only falls
    back to visible task cards when the app does not expose structured responses.
    """

    connector_id='marketing.tasks'
    connector_kind='browser_tasks'
    name='Marketing · tarefas'
    read_only=True

    def __init__(self, *, app_url: str, state_path: Path, secret_store, timeout_ms: int=45000):
        self.app_url=str(app_url).rstrip('/')
        self.state_path=Path(state_path)
        self.secret_store=secret_store
        self.timeout_ms=int(timeout_ms)
        self.state_path.parent.mkdir(parents=True,exist_ok=True)

    def _playwright_ready(self):
        try:
            import playwright.sync_api  # noqa:F401
            return True
        except Exception:
            return False

    def health(self):
        if not self._playwright_ready():
            return {'status':'unavailable','error':'Playwright não instalado','read_only':True,'url':self.app_url}
        has_session=self.state_path.exists()
        has_credentials=bool(self.secret_store.get('marketing_tasks_email') and self.secret_store.get('marketing_tasks_password'))
        return {
            'status':'healthy' if has_session else ('configured' if has_credentials else 'authorization_required'),
            'read_only':True,'url':self.app_url,'session':has_session,
        }

    def connect_interactive(self, email: str, password: str, *, timeout_seconds: int=180):
        if not self._playwright_ready():
            raise RuntimeError('Playwright não está instalado. Execute Setup-Jarvis-Extras.cmd.')
        self.secret_store.set('marketing_tasks_email',email)
        self.secret_store.set('marketing_tasks_password',password)
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=False)
            context=browser.new_context()
            page=context.new_page()
            page.goto(self.app_url,wait_until='domcontentloaded',timeout=self.timeout_ms)
            auto=self._try_login(page,email,password)
            # Give SPA redirects/data hydration time. If auto selectors fail, the
            # visible browser remains available for the user to finish manually.
            try:
                page.wait_for_load_state('networkidle',timeout=min(self.timeout_ms,30000))
            except Exception:
                pass
            if self._looks_like_login(page):
                page.bring_to_front()
                deadline=datetime.now().timestamp()+timeout_seconds
                while datetime.now().timestamp()<deadline:
                    page.wait_for_timeout(1000)
                    if not self._looks_like_login(page):
                        break
            if self._looks_like_login(page):
                browser.close()
                raise RuntimeError('Login não foi confirmado dentro do prazo.')
            context.storage_state(path=str(self.state_path))
            title=page.title()
            url=page.url
            browser.close()
        return {'status':'authorized','url':url,'title':title,'auto_login_attempted':auto,'state_path':str(self.state_path)}

    def disconnect(self):
        self.state_path.unlink(missing_ok=True)
        self.secret_store.delete('marketing_tasks_email')
        self.secret_store.delete('marketing_tasks_password')

    def _looks_like_login(self,page):
        try:
            if page.locator('input[type="password"]').count():
                return True
            text=(page.locator('body').inner_text(timeout=3000) or '').lower()
            return ('entrar' in text or 'login' in text or 'acessar' in text) and ('senha' in text or 'password' in text)
        except Exception:
            return False

    def _try_login(self,page,email,password):
        email_selectors=[
            'input[type="email"]','input[name="email"]','input[autocomplete="email"]',
            'input[placeholder*="mail" i]','input[placeholder*="email" i]',
        ]
        password_selectors=['input[type="password"]','input[name="password"]','input[autocomplete="current-password"]']
        e=None;p=None
        for sel in email_selectors:
            try:
                loc=page.locator(sel)
                if loc.count(): e=loc.first;break
            except Exception: pass
        for sel in password_selectors:
            try:
                loc=page.locator(sel)
                if loc.count(): p=loc.first;break
            except Exception: pass
        if not e or not p:
            return False
        try:
            e.fill(email,timeout=5000);p.fill(password,timeout=5000)
            submitted=False
            for sel in ('button[type="submit"]','input[type="submit"]'):
                loc=page.locator(sel)
                if loc.count(): loc.first.click(timeout=5000);submitted=True;break
            if not submitted:
                for label in ('Entrar','Login','Acessar','Continuar'):
                    loc=page.get_by_role('button',name=re.compile(label,re.I))
                    if loc.count(): loc.first.click(timeout=5000);submitted=True;break
            if not submitted: p.press('Enter')
            return True
        except Exception:
            return False

    def sync(self):
        if not self._playwright_ready():
            raise RuntimeError('Playwright não está instalado.')
        email=self.secret_store.get('marketing_tasks_email')
        password=self.secret_store.get('marketing_tasks_password')
        from playwright.sync_api import sync_playwright
        captures=[]
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True)
            context_kwargs={}
            if self.state_path.exists():
                context_kwargs['storage_state']=str(self.state_path)
            context=browser.new_context(**context_kwargs)
            page=context.new_page()

            def capture(response):
                try:
                    ctype=(response.headers or {}).get('content-type','').lower()
                    url=response.url.lower()
                    if 'json' not in ctype and '/rest/v1/' not in url and 'supabase' not in url:
                        return
                    if response.status>=400:
                        return
                    data=response.json()
                    captures.append({'url':response.url,'data':data})
                except Exception:
                    return
            page.on('response',capture)
            page.goto(self.app_url,wait_until='domcontentloaded',timeout=self.timeout_ms)
            try: page.wait_for_load_state('networkidle',timeout=min(25000,self.timeout_ms))
            except Exception: page.wait_for_timeout(2500)
            if self._looks_like_login(page) and email and password:
                self._try_login(page,email,password)
                try: page.wait_for_load_state('networkidle',timeout=min(25000,self.timeout_ms))
                except Exception: page.wait_for_timeout(2500)
            if self._looks_like_login(page):
                browser.close()
                raise RuntimeError('Sessão expirada. Execute Connect-Marketing-Tasks.cmd.')
            try: context.storage_state(path=str(self.state_path))
            except Exception: pass
            dom_records=self._dom_records(page)
            final_url=page.url
            browser.close()

        records=[]
        seen=set()
        for packet in captures:
            for record in _walk_json(packet['data']):
                marker=json.dumps(record,sort_keys=True,ensure_ascii=False,default=str)[:4000]
                if marker not in seen:
                    seen.add(marker);records.append((record,packet['url']))
        for record in dom_records:
            marker=json.dumps(record,sort_keys=True,ensure_ascii=False,default=str)[:4000]
            if marker not in seen:
                seen.add(marker);records.append((record,self.app_url))

        items=[]
        for idx,(record,source) in enumerate(records[:120]):
            item=self._to_item(record,idx,source)
            if item is not None:
                items.append(item)
        # Keep incomplete/current work first. Completed records are useful for
        # context but intentionally excluded from the morning responsibility list.
        items.sort(key=lambda x:(-x.priority, x.occurred_at or '9999'))
        return SyncResult(items,{'url':final_url,'records_seen':len(records),'tasks':len(items),'read_only':True})

    def _dom_records(self,page):
        selectors='[data-task-id],[data-testid*="task" i],[class*="task" i],[class*="card" i],[draggable="true"],article'
        try:
            rows=page.locator(selectors)
            count=min(rows.count(),80)
        except Exception:
            return []
        out=[]
        for i in range(count):
            try:
                el=rows.nth(i);text=_clean(el.inner_text(timeout=1500),1800)
                if len(text)<3: continue
                if not any(w in text.lower() for w in ('pendente','andamento','fazer','todo','prazo','hoje','amanhã','amanha','conclu','tarefa','post','publica','reuni','projeto')):
                    continue
                out.append({'title':text.split('\n',1)[0][:220],'description':text,'status':'','_dom':True})
            except Exception:
                continue
        return out

    def _to_item(self,record:dict,index:int,source:str):
        title=_clean(_pick(record,_TITLE_KEYS),220)
        if not title:
            return None
        status=_clean(_pick(record,_STATUS_KEYS),80)
        done_value=_pick(record,('completed','done','is_done'),None)
        if done_value is True or str(done_value).lower() in {'1','true','yes','sim'} or status.lower() in _DONE_WORDS:
            return None
        desc=_clean(_pick(record,_DESC_KEYS),1800)
        due=_iso(_pick(record,_DATE_KEYS,None))
        external=_clean(_pick(record,_ID_KEYS,''),180)
        if not external:
            external='browser:'+hashlib.sha256(f'{title}|{status}|{due}'.encode('utf-8')).hexdigest()[:20]
        raw_priority=_pick(record,_PRIORITY_KEYS,50)
        try: priority=int(float(raw_priority))
        except Exception:
            word=str(raw_priority).lower();priority=85 if word in {'high','alta','urgent','urgente'} else (65 if word in {'medium','media','média'} else 50)
        hay=f'{title} {status} {desc}'.lower()
        if any(x in hay for x in ('urgente','hoje','atrasad','overdue')): priority=max(priority,88)
        elif any(x in hay for x in ('andamento','doing','progress')): priority=max(priority,68)
        return ConnectorItem(
            external_id=external,item_type='work_task',title=title,content=desc,
            occurred_at=due,source_uri=source or self.app_url,priority=max(1,min(100,priority)),
            metadata={'status':status,'due_at':due,'app_url':self.app_url,'raw':{str(k):v for k,v in list(record.items())[:30] if isinstance(v,(str,int,float,bool,type(None)))}}
        )
