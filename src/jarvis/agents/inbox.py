from __future__ import annotations

import asyncio

from jarvis.agents.base import AgentCard,AgentResult
from jarvis.core.events import Event
from jarvis.models import ChatMessage


class InboxAgent:
    card=AgentCard(
        'administration.inbox','Inbox','Administration',
        'Classificar e priorizar itens recebidos por connectors autorizados.',
        ('triage','prioritization','inbox'),(), 'fast',True,
    )

    def __init__(self,*,connector_repository,artifact_store,agent_runs,bus,model_registry=None,model_router=None):
        self.connector_repository=connector_repository
        self.artifact_store=artifact_store
        self.agent_runs=agent_runs
        self.bus=bus
        self.model_registry=model_registry
        self.model_router=model_router

    async def _model_triage(self, objective, messages, events):
        if self.model_registry is None or self.model_router is None or not (messages or events):
            return '', None
        route=self.model_router.route(capability=self.card.model_capability,privacy='local')
        provider=self.model_registry.get(route.provider)
        rows=[]
        for item in (messages[:16]+events[:8]):
            detail=' '.join(str(item.get('content') or '').split())[:500]
            rows.append(
                f"- tipo={item.get('item_type')} prioridade={item.get('priority')} "
                f"titulo={item.get('title')} conteudo={detail}"
            )
        prompt=(
            f"OBJETIVO: {objective}\n\nITENS SINCRONIZADOS:\n"+'\n'.join(rows)+
            "\n\nFaça uma triagem curta. Aponte somente o que merece atenção, por quê e a próxima ação sugerida. "
            "Não invente remetentes, datas ou fatos ausentes. Não responda nem altere itens."
        )
        response=await asyncio.to_thread(
            provider.chat,[ChatMessage('user',prompt)],model=route.model,
            system=(
                'Você é Inbox, agente de triagem do Jarvis Next. Trabalhe somente com os itens recebidos. '
                'Separe urgente/importante/rotina quando houver evidência. Seja curto e objetivo.'
            )
        )
        return response.content.strip(), response

    async def run(self,objective,*,task_id,context=''):
        assigned=self.model_router.local_model(self.card.model_capability) if self.model_router else None
        rid=self.agent_runs.start(
            self.card.agent_id,task_id,assigned,{'objective':objective}
        )
        self.agent_runs.update_activity(rid,'Triando caixa de entrada',0.25)
        await self.bus.publish(Event(
            'agent.started',task_id=task_id,agent_id=self.card.agent_id,
            payload={'agent_run_id':rid,'activity':'Triando caixa de entrada','model':assigned}
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

            model_error=None;response=None
            try:
                insight,response=await self._model_triage(objective,messages,events)
                if insight:
                    report.extend(['','## Leitura do agente',insight])
            except Exception as exc:
                model_error=str(exc)
                report.extend(['','## Leitura do agente','- A triagem determinística foi concluída; a camada de modelo local não respondeu neste ciclo.'])

            content='\n'.join(report)
            metadata={
                'items':len(items),'messages':len(messages),'events':len(events),
                'model':response.model if response else assigned,
                'provider':response.provider if response else None,
                'model_error':model_error,
            }
            artifact=self.artifact_store.write_text(
                task_id=task_id,agent_id=self.card.agent_id,
                name='inbox-triage.md',content=content,metadata=metadata
            )
            self.agent_runs.finish(rid,artifact_id=artifact['artifact_id'])
            await self.bus.publish(Event(
                'agent.completed',task_id=task_id,agent_id=self.card.agent_id,
                payload={'agent_run_id':rid,'artifact_id':artifact['artifact_id'],'model':metadata['model']}
            ))
            return AgentResult(True,content,artifact['artifact_id'],artifact['path'],metadata)
        except Exception as exc:
            self.agent_runs.finish(rid,error=str(exc))
            await self.bus.publish(Event(
                'agent.failed',severity='error',task_id=task_id,agent_id=self.card.agent_id,
                payload={'agent_run_id':rid,'error':str(exc)}
            ))
            raise
