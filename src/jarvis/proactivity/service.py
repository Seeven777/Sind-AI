from __future__ import annotations

from datetime import datetime,timezone,timedelta


class OpportunityEngine:
    """Read-only proactive reasoning over current system state.

    It proposes work. It does not create external side effects.
    """

    def __init__(self,*,briefing,tasks):
        self.briefing=briefing
        self.tasks=tasks

    def scan(self):
        snap=self.briefing.snapshot()
        opportunities=[]

        for item in snap.get('priorities',[]):
            kind=item.get('kind')
            if kind=='approval':
                opportunities.append({
                    'kind':'approval',
                    'priority':95,
                    'title':f"Revisar aprovação: {item.get('title')}",
                    'reason':item.get('detail'),
                    'ref':item.get('ref'),
                    'suggested_action':'open_approval',
                })
            elif kind=='inbox':
                opportunities.append({
                    'kind':'inbox',
                    'priority':85,
                    'title':f"Analisar item importante: {item.get('title')}",
                    'reason':item.get('detail'),
                    'ref':item.get('ref'),
                    'suggested_action':'triage_inbox',
                })
            elif kind=='calendar':
                opportunities.append({
                    'kind':'calendar',
                    'priority':80,
                    'title':f"Preparar-se para: {item.get('title')}",
                    'reason':item.get('detail'),
                    'ref':item.get('ref'),
                    'suggested_action':'prepare_meeting',
                })

        # Interrupted work should be visible as a continuation opportunity.
        try:
            from jarvis.tasks import TaskStatus
            interrupted=self.tasks.list_by_status({TaskStatus.INTERRUPTED})
            for task in interrupted[:5]:
                opportunities.append({
                    'kind':'task',
                    'priority':90,
                    'title':f"Retomar tarefa interrompida: {task.title}",
                    'reason':task.objective,
                    'ref':task.task_id,
                    'suggested_action':'resume_task',
                })
        except Exception:
            pass

        opportunities.sort(key=lambda x:x['priority'],reverse=True)
        return {
            'generated_at':datetime.now(timezone.utc).isoformat(),
            'count':len(opportunities),
            'items':opportunities[:12],
        }
