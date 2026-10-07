from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import re

from jarvis.agents.base import AgentCard, AgentResult
from jarvis.core.events import Event
from jarvis.models import ChatMessage


def _normalize(text):
    return re.sub(r'\s+',' ',str(text).strip().lower())


def _age_days(value):
    try:
        dt=datetime.fromisoformat(str(value))
        if dt.tzinfo is None:
            dt=dt.replace(tzinfo=timezone.utc)
        return max(0,(datetime.now(timezone.utc)-dt).days)
    except Exception:
        return 0


class MemoryCuratorAgent:
    card=AgentCard(
        'memory.curator','Memory Curator','Memory',
        'Inspecionar, consolidar e sinalizar duplicidades na memória persistente.',
        ('memory','deduplication','quality'),(), 'fast',True,
    )

    def __init__(self,*,memory_repository,artifact_store,agent_runs,bus,model_registry=None,model_router=None):
        self.memory_repository=memory_repository
        self.artifact_store=artifact_store
        self.agent_runs=agent_runs
        self.bus=bus
        self.model_registry=model_registry
        self.model_router=model_router

    async def _model_review(self, objective, rows, duplicates, stale, relevant):
        if self.model_registry is None or self.model_router is None or not rows:
            return '', None
        route=self.model_router.route(capability=self.card.model_capability,privacy='local')
        provider=self.model_registry.get(route.provider)
        samples=[]
        for item in sorted(rows,key=lambda x:float(x.get('importance') or 0),reverse=True)[:14]:
            samples.append(f"- importância={float(item.get('importance') or 0):.2f} tipo={item.get('memory_type')} :: {str(item.get('content') or '')[:550]}")
        prompt=(
            f"OBJETIVO: {objective}\n\nAMOSTRA DE MEMÓRIAS:\n"+'\n'.join(samples)+
            f"\n\nduplicidades_exatas={len(duplicates)} stale_candidates={len(stale)} relevantes={len(relevant)}\n"
            "Sugira no máximo 5 ações de curadoria: consolidar, manter, revisar ou arquivar futuramente. "
            "Não apague nada, não invente fatos e não reescreva a memória por conta própria."
        )
        response=await asyncio.to_thread(
            provider.chat,[ChatMessage('user',prompt)],model=route.model,
            system=(
                'Você é Memory Curator do Jarvis Next. Seu trabalho é manter contexto útil e coerente. '
                'Você pode recomendar mudanças, mas nunca apagar memória autonomamente.'
            )
        )
        return response.content.strip(),response

    async def run(self,objective,*,task_id,context=''):
        assigned=self.model_router.local_model(self.card.model_capability) if self.model_router else None
        rid=self.agent_runs.start(
            self.card.agent_id,task_id,assigned,{'objective':objective}
        )
        self.agent_runs.update_activity(rid,'Auditando memórias',0.30)
        await self.bus.publish(Event(
            'agent.started',task_id=task_id,agent_id=self.card.agent_id,
            payload={'agent_run_id':rid,'activity':'Auditando memórias','model':assigned}
        ))
        try:
            rows=self.memory_repository.recent(200)
            tokens=[
                token for token in re.findall(r"[\wÀ-ÿ]{4,}", str(objective).lower())
                if token not in {
                    'para','com','uma','sobre','seus','suas','como','este','esta',
                    'missão','missao','precisa','deve','deverá','devera'
                }
            ]
            relevant=[]
            seen=set()
            for token in tokens[:10]:
                for item in self.memory_repository.search(token, limit=12):
                    if item['memory_id'] not in seen:
                        seen.add(item['memory_id'])
                        relevant.append(item)
            groups={}
            for item in rows:
                groups.setdefault(_normalize(item['content']),[]).append(item)
            duplicates=[items for items in groups.values() if len(items)>1]

            stale=[]
            for item in rows:
                age=_age_days(item.get('created_at'))
                importance=float(item.get('importance') or 0)
                if age>=90 and importance<.30:
                    stale.append((age,item))
            stale.sort(key=lambda x:(x[0],-float(x[1].get('importance') or 0)),reverse=True)

            report=[
                '# Curadoria de memória','',
                f'- Memórias analisadas: {len(rows)}',
                f'- Grupos duplicados exatos: {len(duplicates)}',
                f'- Candidatas a arquivamento seletivo: {len(stale)}','',
                '## Memórias de maior importância',
            ]
            for item in sorted(rows,key=lambda x:float(x.get('importance') or 0),reverse=True)[:12]:
                report.append(f"- [{item['memory_type']}] {item['content']}")
            report.extend(['','## Contexto relevante para a missão'])
            if not relevant:
                report.append('- Nenhuma memória relevante foi localizada por correspondência textual.')
            else:
                for item in relevant[:20]:
                    report.append(f"- [{item['memory_type']}] {item['content']}")
            report.extend(['','## Duplicidades encontradas'])
            if not duplicates:
                report.append('- Nenhuma duplicidade exata encontrada.')
            else:
                for idx,items in enumerate(duplicates[:20],1):
                    report.append(f"- Grupo {idx}: {len(items)} ocorrências — {items[0]['content']}")
            report.extend(['','## Candidatas a arquivamento seletivo'])
            if not stale:
                report.append('- Nenhuma memória antiga de baixa importância foi encontrada.')
            else:
                for age,item in stale[:20]:
                    report.append(f"- {age} dias · importância {float(item.get('importance') or 0):.2f} · {item['content']}")

            model_error=None;response=None
            try:
                insight,response=await self._model_review(objective,rows,duplicates,stale,relevant)
                if insight:
                    report.extend(['','## Recomendações do agente',insight])
            except Exception as exc:
                model_error=str(exc)
                report.extend(['','## Recomendações do agente','- Auditoria determinística concluída; o modelo local não respondeu neste ciclo.'])

            report.extend([
                '','## Política',
                'Nenhuma memória foi apagada automaticamente. O agente audita, identifica duplicidades e sinaliza candidatos antigos para consolidação/arquivamento supervisionado.',
            ])
            content='\n'.join(report)
            metadata={
                'memories_scanned':len(rows),'duplicate_groups':len(duplicates),
                'stale_candidates':len(stale),'model':response.model if response else assigned,
                'provider':response.provider if response else None,'model_error':model_error,
            }
            artifact=self.artifact_store.write_text(
                task_id=task_id,agent_id=self.card.agent_id,
                name='memory-curation-report.md',content=content,metadata=metadata
            )
            self.agent_runs.finish(rid,artifact_id=artifact['artifact_id'])
            await self.bus.publish(Event(
                'agent.completed',task_id=task_id,agent_id=self.card.agent_id,
                payload={'agent_run_id':rid,'artifact_id':artifact['artifact_id'],'model':metadata['model']}
            ))
            return AgentResult(
                True,content,artifact['artifact_id'],artifact['path'],
                {
                    **metadata,'relevant_memories':len(relevant),
                    'relevant_context':[x['content'] for x in relevant[:20]],
                }
            )
        except Exception as exc:
            self.agent_runs.finish(rid,error=str(exc))
            await self.bus.publish(Event(
                'agent.failed',severity='error',task_id=task_id,agent_id=self.card.agent_id,
                payload={'agent_run_id':rid,'error':str(exc)}
            ))
            raise
