from __future__ import annotations

from datetime import datetime,timezone,timedelta

from jarvis.tasks import TaskStatus


class BriefingService:
    def __init__(
        self,*,tasks,approvals,artifacts,missions,model_registry,
        connector_repository=None,connector_service=None,watcher_repository=None
    ):
        self.tasks=tasks
        self.approvals=approvals
        self.artifacts=artifacts
        self.missions=missions
        self.model_registry=model_registry
        self.connector_repository=connector_repository
        self.connector_service=connector_service
        self.watcher_repository=watcher_repository

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
        connector_counts={'total':0,'unread':0,'events':0}
        sources=[]
        if self.connector_repository:
            unread=self.connector_repository.unread(limit=12)
            connector_counts=self.connector_repository.counts()
            upcoming=self.connector_repository.upcoming_events(
                datetime.now(timezone.utc).isoformat(),limit=8
            )
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
            },
            'priorities':priorities[:7],
            'upcoming_events':upcoming[:5],
            'recent_inbox':unread[:8],
            'recent_missions':missions,
            'connectors':{
                'health':self.connector_service.health() if self.connector_service else {},
                'sources':sources,
                'counts':connector_counts,
            },
            'watchers':self.watcher_repository.enabled() if self.watcher_repository else [],
            'models':self.model_registry.health(),
        }

    def text(self):
        snap=self.snapshot()
        s=snap['summary']
        lines=['Briefing do Jarvis','']
        if not snap['priorities']:
            lines.append('Nenhuma prioridade crítica detectada nas fontes atualmente conectadas.')
        else:
            lines.append('Prioridades:')
            for item in snap['priorities']:
                lines.append(f"- {item['title']} ({item['kind']}: {item['detail']})")
        lines.extend([
            '',
            f"Caixa de entrada não lida: {s['inbox_unread']}",
            f"Eventos futuros carregados: {s['upcoming_events']}",
            f"Tarefas ativas: {s['active_tasks']}",
            f"Aprovações pendentes: {s['pending_approvals']}",
        ])
        return '\n'.join(lines)
