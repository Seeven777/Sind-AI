from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from .base import ConnectorItem, SyncResult


def _unfold(text:str)->list[str]:
    result=[]
    for line in text.replace('\r\n','\n').replace('\r','\n').split('\n'):
        if line.startswith((' ','\t')) and result:
            result[-1]+=line[1:]
        else:
            result.append(line)
    return result


def _parse_ics_dt(raw:str)->str|None:
    value=raw.strip()
    formats=(
        '%Y%m%dT%H%M%SZ',
        '%Y%m%dT%H%M%S',
        '%Y%m%dT%H%M',
        '%Y%m%d',
    )
    for fmt in formats:
        try:
            dt=datetime.strptime(value,fmt)
            if value.endswith('Z'):
                dt=dt.replace(tzinfo=timezone.utc)
            elif dt.tzinfo is None:
                dt=dt.astimezone()
            return dt.astimezone(timezone.utc).isoformat()
        except ValueError:
            pass
    return None


class ICSCalendarConnector:
    connector_id='local.calendar'
    connector_kind='ics_calendar'
    name='Calendário local ICS'
    read_only=True

    def __init__(self,path:Path):
        self.path=Path(path).resolve()
        self.path.parent.mkdir(parents=True,exist_ok=True)

    def health(self):
        return {
            'status':'healthy' if self.path.is_file() else 'empty',
            'path':str(self.path),'read_only':True
        }

    def sync(self):
        if not self.path.exists():
            return SyncResult([],{ 'path':str(self.path),'events_seen':0,'note':'calendar.ics ainda não existe' })
        text=self.path.read_text(encoding='utf-8',errors='replace')
        lines=_unfold(text)
        events=[]; current=None
        for line in lines:
            if line=='BEGIN:VEVENT':
                current={}
                continue
            if line=='END:VEVENT':
                if current is not None:
                    events.append(current)
                current=None
                continue
            if current is None or ':' not in line:
                continue
            left,value=line.split(':',1)
            key=left.split(';',1)[0].upper()
            current[key]=value.strip()

        items=[]
        for event in events:
            title=event.get('SUMMARY') or '(evento sem título)'
            start=_parse_ics_dt(event.get('DTSTART',''))
            uid=event.get('UID') or hashlib.sha256(
                f"{title}|{event.get('DTSTART','')}|{event.get('LOCATION','')}".encode('utf-8')
            ).hexdigest()
            description=event.get('DESCRIPTION','').replace('\\n','\n')
            location=event.get('LOCATION','')
            content='\n'.join(x for x in (
                description,
                f'Local: {location}' if location else '',
            ) if x)
            items.append(ConnectorItem(
                external_id=uid,
                item_type='calendar_event',
                title=title,
                content=content,
                occurred_at=start,
                source_uri=str(self.path),
                priority=70,
                metadata={
                    'location':location,
                    'dtstart_raw':event.get('DTSTART'),
                    'dtend_raw':event.get('DTEND'),
                    'uid':uid,
                }
            ))
        return SyncResult(items,{'path':str(self.path),'events_seen':len(items)})
