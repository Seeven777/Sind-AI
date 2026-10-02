from __future__ import annotations

from jarvis.agents.catalog import builtin_agent_cards
from jarvis.tasks import TaskStatus

OFFICE_STATUS={'running':'working','failed':'error','completed':'idle'}
ROOM_ORDER=('Research','Intelligence','Creative','Engineering','Operations','Review','Administration','Memory')

class HQService:
    def __init__(
        self,agent_runs,tasks,approvals,events,*,missions=None,workspace=None,
        connector_repository=None,watcher_repository=None,agent_registry=None
    ):
        self.agent_runs=agent_runs; self.tasks=tasks; self.approvals=approvals
        self.events=events; self.missions=missions; self.workspace=workspace or {}
        self.connector_repository=connector_repository
        self.watcher_repository=watcher_repository
        self.agent_registry=agent_registry

    def _agent_rows(self,cards):
        latest=self.agent_runs.latest_runs()
        agents=[]
        for card in cards:
            run=latest.get(card.agent_id)
            backend_status=run.get('status') if run else None
            status=OFFICE_STATUS.get(backend_status,'idle' if card.active else 'planned')
            agents.append({
                'id':card.agent_id,'name':card.name,'department':card.department,
                'available':card.active,'status':status,'last_status':backend_status,
                'task_id':run.get('task_id') if run else None,
                'model':run.get('model') if run else None,
                'activity':run.get('activity') if run else ('Disponível' if card.active else 'Planejado'),
                'progress':float(run.get('progress') or 0.0) if run else 0.0,
                'started_at':run.get('started_at') if run else None,
                'ended_at':run.get('ended_at') if run else None,
                'error':run.get('last_error') if run else None,
                'mission':card.mission,'capabilities':list(card.capabilities),
            })
        return agents

    def agent_directory(self):
        cards=self.agent_registry.cards() if self.agent_registry is not None else builtin_agent_cards()
        return self._agent_rows(cards)

    def snapshot(self):
        # The visual HQ keeps the small core team. The full imported catalog is
        # exposed by agent_directory() so the office does not become unreadable.
        agents=self._agent_rows(builtin_agent_cards())
        departments={name:[] for name in ROOM_ORDER}
        for agent in agents: departments.setdefault(agent['department'],[]).append(agent)

        active_states={
            TaskStatus.CREATED,TaskStatus.PLANNING,TaskStatus.READY,TaskStatus.RUNNING,
            TaskStatus.PAUSED,TaskStatus.BLOCKED,TaskStatus.VERIFYING,TaskStatus.INTERRUPTED,
        }
        tasks=[{
            'id':t.task_id,'title':t.title,'objective':t.objective,'status':t.status.value,
            'priority':t.priority,'checkpoint':t.checkpoint_seq,'updated_at':t.updated_at,'error':t.last_error
        } for t in self.tasks.list_by_status(active_states)]

        attention=[{
            'kind':'approval','id':row['approval_id'],'task_id':row['task_id'],
            'title':row['action'],'risk':row['risk'],'requested_at':row['requested_at'],
            'payload':row.get('payload') or {}
        } for row in self.approvals.pending()]
        for task in tasks:
            if task['status'] in {'blocked','interrupted'}:
                attention.append({
                    'kind':'task','id':task['id'],'task_id':task['id'],
                    'title':task['title'],'risk':task['status'],'requested_at':task['updated_at']
                })

        timeline=[{
            'type':event['event_type'],'timestamp':event['timestamp'],
            'task_id':event.get('task_id'),'agent_id':event.get('agent_id'),
            'severity':event['severity'],'payload':event['payload']
        } for event in self.events.recent(40)]

        missions=self.missions.recent(12) if self.missions else []
        connector_counts=self.connector_repository.counts() if self.connector_repository else {'total':0,'unread':0,'events':0}
        connector_sources=self.connector_repository.sources() if self.connector_repository else []
        watchers=self.watcher_repository.enabled() if self.watcher_repository else []
        return {
            'schema':'jarvis.hq.snapshot.v2',
            'core':{'name':'Jarvis','status':'ready'},
            'workspace':{
                'id':self.workspace.get('workspace_id'),'name':self.workspace.get('name','Principal')
            },
            'office':{'theme':'agent-office-inspired','rooms':list(departments.keys())},
            'departments':departments,'missions':missions,'tasks':tasks,
            'attention':attention,'timeline':timeline,
            'connectors':{'counts':connector_counts,'sources':connector_sources},
            'watchers':watchers,
            'metrics':{
                'agents_total':len(agents),
                'agents_available':sum(1 for a in agents if a['available']),
                'agents_working':sum(1 for a in agents if a['status']=='working'),
                'missions_active':sum(1 for m in missions if m['status'] not in {'completed','failed','cancelled'}),
                'needs_you':len(attention),
                'inbox_unread':connector_counts.get('unread',0),
                'connector_sources':len(connector_sources),
                'watchers_enabled':len(watchers),
            },
        }
