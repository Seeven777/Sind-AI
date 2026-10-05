from __future__ import annotations

import re

from jarvis.agents.base import AgentCard, AgentResult
from jarvis.core.events import Event


def _normalize(text):
    return re.sub(r'\s+',' ',str(text).strip().lower())


class MemoryCuratorAgent:
    card=AgentCard(
        'memory.curator','Memory Curator','Memory',
        'Inspecionar, consolidar e sinalizar duplicidades na memória persistente.',
        ('memory','deduplication','quality'),(), 'fast',True,
    )

    def __init__(self,*,memory_repository,artifact_store,agent_runs,bus):
        self.memory_repository=memory_repository
        self.artifact_store=artifact_store
        self.agent_runs=agent_runs
        self.bus=bus

    async def run(self,objective,*,task_id,context=''):
        rid=self.agent_runs.start(
            self.card.agent_id,task_id,None,{'objective':objective}
        )
        self.agent_runs.update_activity(rid,'Auditando memórias',0.30)
        await self.bus.publish(Event(
            'agent.started',task_id=task_id,agent_id=self.card.agent_id,
            payload={'agent_run_id':rid,'activity':'Auditando memórias'}
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
            report=[
                '# Curadoria de memória',
                '',
                f'- Memórias analisadas: {len(rows)}',
                f'- Grupos duplicados exatos: {len(duplicates)}',
                '',
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
            report.extend([
                '',
                '## Política',
                'Nenhuma memória foi apagada automaticamente. Este agente apenas audita e produz evidência.',
            ])
            content='\n'.join(report)
            artifact=self.artifact_store.write_text(
                task_id=task_id,agent_id=self.card.agent_id,
                name='memory-curation-report.md',content=content,
                metadata={'memories_scanned':len(rows),'duplicate_groups':len(duplicates)}
            )
            self.agent_runs.finish(rid,artifact_id=artifact['artifact_id'])
            await self.bus.publish(Event(
                'agent.completed',task_id=task_id,agent_id=self.card.agent_id,
                payload={'agent_run_id':rid,'artifact_id':artifact['artifact_id']}
            ))
            return AgentResult(
                True,content,artifact['artifact_id'],artifact['path'],
                {'memories_scanned':len(rows),'relevant_memories':len(relevant),'relevant_context':[x['content'] for x in relevant[:20]],'duplicate_groups':len(duplicates)}
            )
        except Exception as exc:
            self.agent_runs.finish(rid,error=str(exc))
            await self.bus.publish(Event(
                'agent.failed',severity='error',task_id=task_id,agent_id=self.card.agent_id,
                payload={'agent_run_id':rid,'error':str(exc)}
            ))
            raise
