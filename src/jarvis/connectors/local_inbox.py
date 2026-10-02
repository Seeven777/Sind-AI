from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from .base import ConnectorItem, SyncResult


_TEXT_EXTS={'.txt','.md','.json','.csv','.log','.py','.js','.ts','.html','.css','.toml','.yaml','.yml'}


class LocalInboxConnector:
    connector_id='local.inbox'
    connector_kind='local_inbox'
    name='Caixa de entrada local'
    read_only=True

    def __init__(self,root:Path,max_chars:int=12000):
        self.root=Path(root).resolve()
        self.max_chars=max_chars
        self.root.mkdir(parents=True,exist_ok=True)

    def health(self):
        return {
            'status':'healthy' if self.root.is_dir() else 'unavailable',
            'path':str(self.root),'read_only':True
        }

    def sync(self):
        items=[]
        for path in sorted(self.root.glob('*'),key=lambda p:p.stat().st_mtime if p.exists() else 0,reverse=True):
            if not path.is_file():
                continue
            stat=path.stat()
            digest=hashlib.sha256(
                f'{path.name}|{stat.st_size}|{stat.st_mtime_ns}'.encode('utf-8')
            ).hexdigest()
            content=''
            if path.suffix.lower() in _TEXT_EXTS:
                try:
                    content=path.read_text(encoding='utf-8',errors='replace')[:self.max_chars]
                except Exception:
                    content=''
            occurred=datetime.fromtimestamp(stat.st_mtime,tz=timezone.utc).isoformat()
            priority=self._priority(path,content)
            items.append(ConnectorItem(
                external_id=digest,
                item_type='message',
                title=path.stem,
                content=content,
                occurred_at=occurred,
                source_uri=str(path),
                priority=priority,
                metadata={
                    'filename':path.name,'extension':path.suffix.lower(),
                    'size':stat.st_size,'local_path':str(path)
                }
            ))
        return SyncResult(items,{'path':str(self.root),'files_seen':len(items)})

    def _priority(self,path,content):
        hay=(path.name+' '+content[:1500]).lower()
        high=('urgente','urgent','prazo','deadline','aprovação','aprovacao','hoje','importante')
        return 85 if any(term in hay for term in high) else 50
