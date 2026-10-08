from __future__ import annotations

from datetime import datetime,timezone,timedelta

from jarvis.tasks import TaskStatus


class BriefingService:
    def __init__(
        self,*,tasks,approvals,artifacts,missions,model_registry,
        connector_repository=None,connector_service=None,watcher_repository=None,autonomy_repository=None
    ):
        self.tasks=tasks
        self.approvals=approvals
        self.artifacts=artifacts
        self.missions=missions
        self.model_registry=model_registry
        self.connector_repository=connector_repository
        self.connector_service=connector_service
        self.watcher_repository=watcher_repository
        self.autonomy_repository=autonomy_repository

    def snapshot(self):
        active_states={
            TaskStatus.CREATED,TaskStatus.PLANNING,TaskStatus.READY,TaskStatus.RUNNING,
            TaskStatus.PAUSED,TaskStatus.BLOCKED,TaskStatus.VERIFYING,TaskStatus.INTERRUPTED,
        }
        tasks=self.tasks.list_by_status(active_states)
        approvals=self.approvals.pending()
        recent_artifacts=self.artifacts.recent(5)
        missions=self.missions.recent(5)

        unread=[]
        upcoming=[]
        marketing_tasks=[]
        connector_counts={'total':0,'unread':0,'events':0}
        sources=[]
        if self.connector_repository:
            unread=self.connector_repository.unread(limit=12)
            connector_counts=self.connector_repository.counts()
            upcoming=self.connector_repository.upcoming_events(
                datetime.now(timezone.utc).isoformat(),limit=8
            )
            try:
                marketing_tasks=self.connector_repository.by_connector('marketing.tasks',limit=20,item_type='work_task')
            except Exception:
                marketing_tasks=[]
            sources=self.connector_repository.sources()

        priorities=[]
        for approval in approvals[:3]:
            priorities.append({
                'kind':'approval','title':approval['action'],
                'detail':approval['risk'],'ref':approval['approval_id']
            })
        for item in unread:
            if int(item.get('priority') or 0)>=80:
                priorities.append({
                    'kind':'inbox','title':item['title'],
                    'detail':f"prioridade {item['priority']}",
                    'ref':item['item_id']
                })
        now=datetime.now(timezone.utc)
        for event in upcoming:
            try: event_dt=datetime.fromisoformat(event['occurred_at'])
            except Exception: continue
            if event_dt<=now+timedelta(hours=24):
                priorities.append({
                    'kind':'calendar','title':event['title'],
                    'detail':event['occurred_at'],'ref':event['item_id']
                })
        for task in tasks[:3]:
            priorities.append({
                'kind':'task','title':task.title,'detail':task.status.value,'ref':task.task_id
            })

        autonomy={}
        if self.autonomy_repository:
            autonomy={
                'daily':self.autonomy_repository.get_state('daily_briefing',{}) or {},
                'discoveries':self.autonomy_repository.recent_discoveries(5),
                'improvements':self.autonomy_repository.proposals('pending',5),
                'attention':self.autonomy_repository.notifications(limit=8),
                'stats':self.autonomy_repository.stats(),
            }

        return {
            'schema':'jarvis.briefing.v2',
            'generated_at':datetime.now(timezone.utc).isoformat(),
            'summary':{
                'active_tasks':len(tasks),
                'pending_approvals':len(approvals),
                'recent_artifacts':len(recent_artifacts),
                'inbox_unread':connector_counts['unread'],
                'upcoming_events':len(upcoming),
                'connector_sources':len(sources),
                'marketing_tasks':len(marketing_tasks),
            },
            'priorities':priorities[:7],
            'upcoming_events':upcoming[:5],
            'recent_inbox':unread[:8],
            'recent_missions':missions,
            'marketing_tasks':marketing_tasks[:12],
            'connectors':{
                'health':self.connector_service.health() if self.connector_service else {},
                'sources':sources,
                'counts':connector_counts,
            },
            'watchers':self.watcher_repository.enabled() if self.watcher_repository else [],
            'models':self.model_registry.health(),
            'autonomy':autonomy,
        }

    def morning_sequence(self):
        snap=self.snapshot()
        daily=(snap.get('autonomy') or {}).get('daily') or {}
        weather=daily.get('weather') or {}
        structured=weather.get('structured') or {}
        current=structured.get('current') or {}
        today=structured.get('today') or {}
        units=structured.get('units') or {}
        hourly=structured.get('hourly') or []
        weather_payload={
            'location':structured.get('location') or daily.get('location') or 'Local configurado',
            'summary':weather.get('summary') or 'Previsão indisponível.',
            'current':current,'today':today,'hourly':hourly[:8],'units':units,
            'sources':weather.get('sources') or [],
        }
        news=[]
        for i,item in enumerate((daily.get('news') or [])[:8]):
            if not isinstance(item,dict):continue
            news.append({
                'id':f'news-{i+1}',
                'title':str(item.get('title') or 'Notícia')[:220],
                'summary':str(item.get('summary') or '')[:520],
                'url':item.get('url'),
                'source':item.get('source') or '',
            })
        tasks=[]
        for i,item in enumerate((snap.get('marketing_tasks') or [])[:10]):
            meta=item.get('metadata') or {}
            tasks.append({
                'id':item.get('item_id') or f'task-{i+1}',
                'title':item.get('title') or 'Tarefa',
                'detail':item.get('content') or '',
                'status':meta.get('status') or '',
                'due_at':meta.get('due_at') or item.get('occurred_at'),
                'priority':item.get('priority') or 50,
                'url':meta.get('app_url') or item.get('source_uri'),
            })
        improvements=(snap.get('autonomy') or {}).get('improvements') or []
        return {
            'schema':'jarvis.morning.v1',
            'generated_at':datetime.now(timezone.utc).isoformat(),
            'greeting':'Bom dia, senhor.',
            'weather':weather_payload,
            'news':news,
            'tasks':tasks,
            'improvements_pending':len([x for x in improvements if x.get('status')=='pending']),
            'closing':'O que faremos hoje?',
            'sources':snap.get('connectors',{}).get('sources',[]),
        }

    def text(self, snap=None):
        snap=snap or self.snapshot()
        s=snap['summary']
        lines=['Briefing do Jarvis','']

        healthy=[]
        unavailable=[]
        for source in snap.get('connectors',{}).get('sources',[]):
            label=source.get('name') or source.get('connector_id') or 'Connector'
            status=str(source.get('status') or 'unknown')
            if status=='healthy': healthy.append(label)
            elif status in {'error','unavailable','authorization_required','unconfigured'}:
                unavailable.append(f"{label}: {status}")
        if healthy:
            lines.append('Fontes sincronizadas: '+', '.join(healthy)+'.')
        if unavailable:
            lines.append('Fontes com atenção: '+', '.join(unavailable)+'.')

        if not snap['priorities']:
            lines.append('Nenhuma prioridade crítica detectada nas fontes conectadas.')
        else:
            lines.extend(['','Prioridades:'])
            for item in snap['priorities']:
                lines.append(f"- {item['title']} ({item['kind']}: {item['detail']})")

        lines.extend(['','Próximos compromissos:'])
        upcoming=snap.get('upcoming_events') or []
        if not upcoming:
            lines.append('- Nenhum evento futuro encontrado nas fontes sincronizadas.')
        else:
            for item in upcoming[:5]:
                when=item.get('occurred_at') or 'horário não informado'
                meta=item.get('metadata') or {}
                location=meta.get('location') or ''
                suffix=f" · {location}" if location else ''
                lines.append(f"- {item.get('title') or '(evento sem título)'} — {when}{suffix}")

        lines.extend(['','E-mails / caixa de entrada recentes:'])
        recent=[x for x in (snap.get('recent_inbox') or []) if x.get('item_type')!='calendar_event']
        if not recent:
            lines.append('- Nenhum item não lido encontrado nas fontes sincronizadas.')
        else:
            for item in recent[:6]:
                meta=item.get('metadata') or {}
                sender=meta.get('from') or ''
                suffix=f" · {sender}" if sender else ''
                lines.append(f"- {item.get('title') or '(sem assunto)'}{suffix}")

        lines.extend([
            '',
            f"Caixa de entrada não lida: {s['inbox_unread']}",
            f"Eventos futuros carregados: {s['upcoming_events']}",
            f"Tarefas ativas: {s['active_tasks']}",
            f"Aprovações pendentes: {s['pending_approvals']}",
        ])
        return '\n'.join(lines)
