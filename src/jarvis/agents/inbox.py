from __future__ import annotations

from jarvis.agents.base import AgentCard,AgentResult
from jarvis.core.events import Event


class InboxAgent:
    card=AgentCard(
        'administration.inbox','Inbox','Administration',
        'Classificar e priorizar itens recebidos por connectors autorizados.',
        ('triage','prioritization','inbox'),(), 'fast',True,
    )

    def __init__(self,*,connector_repository,artifact_store,agent_runs,bus):
        self.connector_repository=connector_repository
        self.artifact_store=artifact_store
        self.agent_runs=agent_runs
        self.bus=bus

    async def run(self,objective,*,task_id,context=''):
        rid=self.agent_runs.start(
            self.card.agent_id,task_id,None,{'objective':objective}
        )
        self.agent_runs.update_activity(rid,'Triando caixa de entrada',0.25)
        await self.bus.publish(Event(
            'agent.started',task_id=task_id,agent_id=self.card.agent_id,
            payload={'agent_run_id':rid,'activity':'Triando caixa de entrada'}
        ))
        try:
            items=self.connector_repository.unread(limit=30)
            events=[x for x in items if x['item_type']=='calendar_event']
            messages=[x for x in items if x['item_type']!='calendar_event']
            messages=sorted(
                messages,key=lambda x:(int(x.get('priority') or 0),x.get('occurred_at') or x['received_at']),
                reverse=True
            )
            report=['# Inbox — triagem','','## Resumo']
            report.append(f'- Itens não lidos: {len(items)}')
            report.append(f'- Mensagens/arquivos: {len(messages)}')
            report.append(f'- Eventos de calendário ainda não lidos: {len(events)}')
            report.extend(['','## Prioridades'])
            if not messages:
                report.append('- Nenhum item pendente.')
            else:
                for item in messages[:12]:
                    mark='ALTA' if int(item.get('priority') or 0)>=80 else 'NORMAL'
                    detail=(item.get('content') or '').strip().replace('\n',' ')
                    if len(detail)>180: detail=detail[:177]+'...'
                    report.append(f"- [{mark}] {item['title']} — {detail or item.get('source_uri') or ''}")
            artifact=self.artifact_store.write_text(
                task_id=task_id,agent_id=self.card.agent_id,
                name='inbox-triage.md',content='\n'.join(report),
                metadata={'items':len(items),'messages':len(messages),'events':len(events)}
            )
            self.agent_runs.finish(rid,artifact_id=artifact['artifact_id'])
            await self.bus.publish(Event(
                'agent.completed',task_id=task_id,agent_id=self.card.agent_id,
                payload={'agent_run_id':rid,'artifact_id':artifact['artifact_id']}
            ))
            return AgentResult(
                True,'\n'.join(report),artifact['artifact_id'],artifact['path'],
                {'items':len(items),'messages':len(messages),'events':len(events)}
            )
        except Exception as exc:
            self.agent_runs.finish(rid,error=str(exc))
            await self.bus.publish(Event(
                'agent.failed',severity='error',task_id=task_id,agent_id=self.card.agent_id,
                payload={'agent_run_id':rid,'error':str(exc)}
            ))
            raise
