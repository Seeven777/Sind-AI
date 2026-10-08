from __future__ import annotations

import asyncio
import json
from datetime import datetime

from jarvis.agents.artifact_agent import ArtifactAgent
from jarvis.agents.base import AgentCard,AgentResult
from jarvis.core.events import Event
from jarvis.models import ChatMessage


class ResearchAgent(ArtifactAgent):
    card=AgentCard(
        'research.general','Research','Research',
        'Investigar problemas usando fontes disponíveis, web e contexto persistente.',
        ('research','web_research','source_validation','synthesis'),
        ('web.search','web.fetch','weather.forecast'),'reasoning',True,
    )
    artifact_name='research-report.md'
    system_prompt="""Você é Research, agente especialista do Jarvis Next.
Trabalhe somente com o contexto e as fontes explicitamente entregues.
Quando houver fontes web:
- cite URLs junto aos achados relevantes;
- nunca invente data, nome, número, documento ou status que não apareça no material recebido;
- diferencie fato encontrado, inferência e hipótese;
- não invente acesso a fontes que não estejam no material;
- destaque conflitos e lacunas;
- prefira fontes primárias e institucionais quando elas aparecerem.
Produza uma síntese útil, riscos, evidências, lacunas e próximos passos.
Escreva em português do Brasil."""

    def __init__(self,*,tool_executor=None,web_enabled=True,**kwargs):
        super().__init__(**kwargs)
        self.tool_executor=tool_executor
        self.web_enabled=web_enabled

    async def run(self,objective:str,*,task_id:str,context:str="",allow_external:bool|None=None)->AgentResult:
        web_context=""
        sources=[]
        use_external = self.web_enabled if allow_external is None else bool(allow_external)
        structured_weather=None
        lowered=objective.lower()
        is_weather=any(x in lowered for x in ('clima','tempo','temperatura','chuva','meteorológ','meteorolog'))
        if self.tool_executor is not None and use_external:
            await self.bus.publish(Event(
                'agent.progress',task_id=task_id,agent_id=self.card.agent_id,
                payload={'progress':0.12,'activity':'Pesquisando fontes públicas'}
            ))
            if is_weather:
                location='São Paulo, SP'
                if 'local padrão:' in lowered:
                    raw=objective.split('LOCAL PADRÃO:',1)[-1]
                    location=raw.split('. ',1)[0].strip() or location
                weather=await self.tool_executor.execute('weather.forecast',{'location':location},task_id=task_id)
                if weather.success:
                    structured_weather=weather.output
                    sources=[{'title':'Open-Meteo','url':'https://open-meteo.com/','content':json.dumps(weather.output,ensure_ascii=False)}]
                    web_context='DADOS METEOROLÓGICOS ESTRUTURADOS (Open-Meteo):\n'+json.dumps(weather.output,ensure_ascii=False,indent=2)
                    await self.bus.publish(Event(
                        'agent.progress',task_id=task_id,agent_id=self.card.agent_id,
                        payload={'progress':0.40,'activity':'Previsão meteorológica obtida'}
                    ))
            if structured_weather is None:
                queries=[objective]
                lowered=objective.lower()
                if 'sindpetshop' in lowered:
                    queries += [
                        'site:sindpetshop.org.br SindPetshop-SP',
                        'site:sindpetshop.org.br convenção coletiva SindPetshop-SP',
                        'site:sindpetshop.org.br sindicato pet shop São Paulo',
                        '"SindPetshop-SP" trabalhadores São Paulo',
                    ]
                queries=list(dict.fromkeys(queries))[:5]
                collected=[];seen=set()
                for idx,query in enumerate(queries,1):
                    search=await self.tool_executor.execute('web.search',{'query':query,'limit':8},task_id=task_id)
                    if search.success:
                        for item in search.output.get('results',[]):
                            url=str(item.get('url') or '').strip()
                            if not url or url in seen: continue
                            seen.add(url);collected.append(item)
                            if len(collected)>=10: break
                    await self.bus.publish(Event(
                        'agent.progress',task_id=task_id,agent_id=self.card.agent_id,
                        payload={'progress':min(.40,.16+idx*.055),'activity':f'Fontes coletadas: {len(collected)}'}
                    ))
                    if len(collected)>=10: break
                fetched=[]
                for item in collected[:6]:
                    fetch=await self.tool_executor.execute('web.fetch',{'url':item['url']},task_id=task_id)
                    record={'title':item.get('title'),'url':item.get('url')}
                    if fetch.success:
                        record['content']=fetch.output.get('content','')[:8000]
                        record['page_title']=fetch.output.get('title','')
                    fetched.append(record)
                sources=fetched or collected
                blocks=[]
                for i,item in enumerate(sources,1):
                    blocks.append(
                        f"FONTE {i}\nURL: {item.get('url','')}\n"
                        f"TÍTULO: {item.get('page_title') or item.get('title') or ''}\n"
                        f"CONTEÚDO EXTRAÍDO:\n{item.get('content','(apenas resultado de busca)')}"
                    )
                web_context='\n\n'.join(blocks)


        route=self.model_router.route(capability=self.card.model_capability,privacy='local')
        provider=self.model_registry.get(route.provider)
        rid=self.agent_runs.start(
            self.card.agent_id,task_id,route.model,
            {'objective':objective,'context_chars':len(context),'sources':len(sources)}
        )
        self.agent_runs.update_activity(rid,'Analisando pesquisa',0.45)
        await self.bus.publish(Event(
            'agent.started',task_id=task_id,agent_id=self.card.agent_id,
            payload={'agent_run_id':rid,'model':route.model,'activity':'Analisando pesquisa'}
        ))
        try:
            parts=[f"DATA ATUAL DO SISTEMA: {datetime.now().astimezone().strftime('%Y-%m-%d')}\nMISSÃO:\n{objective}"]
            if context:
                parts.append(f"CONTEXTO RECEBIDO:\n{context}")
            if web_context:
                parts.append(f"FONTES WEB COLETADAS PELO SISTEMA:\n{web_context}")
            elif self.tool_executor is not None and use_external:
                parts.append(
                    "OBSERVAÇÃO: a pesquisa web não retornou evidência utilizável. "
                    "Não trate conhecimento geral como verificado."
                )
            response=await asyncio.to_thread(
                provider.chat,[ChatMessage('user','\n\n'.join(parts))],
                model=route.model,system=self.system_prompt
            )
            content=response.content.strip()
            if len(content)<60:
                raise RuntimeError('Research produziu uma entrega insuficiente.')
            if sources:
                content += "\n\n## Fontes coletadas pelo Jarvis\n"
                for item in sources:
                    content += f"- {item.get('title') or item.get('page_title') or 'Fonte'} — {item.get('url')}\n"

            self.agent_runs.update_activity(rid,'Salvando pesquisa',0.88)
            artifact=self.artifact_store.write_text(
                task_id=task_id,agent_id=self.card.agent_id,
                name=self.artifact_name,content=content,
                metadata={
                    'provider':response.provider,'model':response.model,
                    'route_reason':route.reason,
                    'sources':[{'title':x.get('title'),'url':x.get('url')} for x in sources],
                }
            )
            self.agent_runs.finish(rid,artifact_id=artifact['artifact_id'])
            await self.bus.publish(Event(
                'artifact.created',task_id=task_id,agent_id=self.card.agent_id,
                payload={
                    'artifact_id':artifact['artifact_id'],'name':artifact['name'],
                    'path':artifact['path'],'sources':len(sources)
                }
            ))
            await self.bus.publish(Event(
                'agent.completed',task_id=task_id,agent_id=self.card.agent_id,
                payload={'agent_run_id':rid,'artifact_id':artifact['artifact_id'],'activity':'Concluído'}
            ))
            return AgentResult(
                True,content,artifact['artifact_id'],artifact['path'],
                {'model':response.model,'provider':response.provider,'sources':sources,'weather':structured_weather}
            )
        except Exception as exc:
            self.agent_runs.finish(rid,error=str(exc))
            await self.bus.publish(Event(
                'agent.failed',severity='error',task_id=task_id,agent_id=self.card.agent_id,
                payload={'agent_run_id':rid,'error':str(exc)}
            ))
            raise
