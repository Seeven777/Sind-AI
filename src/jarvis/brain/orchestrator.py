from __future__ import annotations

import asyncio
import re


from jarvis.core.events import Event
from jarvis.models import ChatMessage
from jarvis.tasks import TaskStatus

JARVIS_SYSTEM="""Você é Jarvis Next, a inteligência central e orquestradora de um sistema pessoal de agentes.
Responda em português do Brasil. Seja direto e útil.
Nunca diga que executou uma ação que não foi realmente executada.
Research, Analyst, Creator, Developer, Operator, Reviewer, Inbox e Memory Curator são capacidades do sistema.
Acesso a e-mail, calendário, internet, arquivos e outras fontes depende do estado REAL dos conectores e ferramentas informado no contexto do runtime.
Nunca diga que uma integração está indisponível quando o contexto do runtime disser que ela está saudável; também nunca invente dados que não estejam sincronizados.
Quando uma ação real for necessária, use Operator e ferramentas registradas.
Ações de escrita exigem aprovação conforme política."""

class JarvisOrchestrator:
    def __init__(
        self,*,intent_router,model_registry,model_router,agent_registry,task_service,
        memory,bus,team_missions=None,briefing=None,tool_planner=None,ai_mesh=None
    ):
        self.intent_router=intent_router
        self.model_registry=model_registry
        self.model_router=model_router
        self.agent_registry=agent_registry
        self.task_service=task_service
        self.memory=memory
        self.bus=bus
        self.team_missions=team_missions
        self.briefing=briefing
        self.tool_planner=tool_planner
        self.ai_mesh=ai_mesh

    async def handle(self,text,*,conversation_history=None,mode='auto'):
        stripped=text.strip()
        lowered=stripped.lower()
        explicit_mode=str(mode or 'auto').lower().strip()
        if lowered.startswith('/hermes'):
            explicit_mode='hermes'
            stripped=stripped[len('/hermes'):].strip()
            lowered=stripped.lower()
        if lowered.startswith('/deep'):
            explicit_mode='deep'
            stripped=stripped[len('/deep'):].strip()
            lowered=stripped.lower()
        if explicit_mode=='hermes' and self.ai_mesh is not None:
            prompt=stripped
            if not prompt:
                return {'kind':'hermes','agent':'hermes','content':'Use: /hermes sua solicitação'}
            if conversation_history:
                prompt = self._with_history(prompt, conversation_history)
            result=await self.ai_mesh.hermes.run(prompt)
            return {
                'kind':'hermes','agent':'hermes','content':result.content,
                'metadata':result.metadata,
            }
        if explicit_mode=='deep':
            prompt=stripped
            if not prompt:
                return {'kind':'deep','agent':'nvidia_nemotron','content':'Use: /deep sua solicitação','mode':'deep'}
            route=self.model_router.route(
                capability='reasoning',
                privacy=self.model_router.privacy_mode,
                budget='premium',
            )
            provider=self.model_registry.get(route.provider)
            if conversation_history:
                prompt=self._with_history(prompt, conversation_history)
            response=await asyncio.to_thread(
                provider.chat,[ChatMessage('user',prompt)],model=route.model,
                system=JARVIS_SYSTEM+self._runtime_context()+'\nVocê está no modo de raciocínio profundo. Entregue somente a resposta final.'
            )
            return {
                'kind':'deep','agent':route.provider,'content':response.content,
                'provider':response.provider,'model':response.model,
                'metadata':{'route_reason':route.reason},'mode':'deep',
            }
        intent=self.intent_router.classify(text)
        await self.bus.publish(Event(
            'jarvis.intent',
            payload={'intent':intent.name,'confidence':intent.confidence,'reason':intent.reason}
        ))

        if intent.name=='briefing' and self.briefing:
            await self._sync_connectors_for_personal_context()
            snap=self.briefing.snapshot()
            return {
                'kind':'briefing','agent':'jarvis',
                'content':self.briefing.text(snap),
                'metadata':snap['summary']
            }
        if intent.name=='inbox':
            await self._sync_connectors_for_personal_context()
            return await self._delegate_agent(
                'administration.inbox','Triagem da caixa de entrada',text,min_chars=20,conversation_history=conversation_history
            )
        if intent.name=='tool_plan' and self.tool_planner:
            return await self._delegate_tool_plan(text)
        if intent.name=='team_mission' and self.team_missions:
            objective=self._with_history(text, conversation_history or []) if conversation_history else text
            return await self.team_missions.run(objective,title='Missão delegada pelo Jarvis')
        if intent.name=='research':
            return await self._delegate_agent(
                'research.general','Missão de pesquisa',text,min_chars=40,conversation_history=conversation_history
            )
        if intent.name=='developer':
            return await self._delegate_agent(
                'engineering.developer','Missão de desenvolvimento',text,min_chars=60,conversation_history=conversation_history
            )
        if intent.name=='memory_curator':
            return await self._delegate_agent(
                'memory.curator','Curadoria de memória',text,min_chars=20,conversation_history=conversation_history
            )
        if intent.name.startswith('operator_'):
            return await self._delegate_operator(intent.name,text)

        route=self.model_router.route(capability='chat',privacy='local')
        provider=self.model_registry.get(route.provider)
        memories=self.memory.context(text,limit=4)
        block=''
        if memories:
            block='\n\nContexto persistente disponível:\n'+'\n'.join(f"- {x['content']}" for x in memories)
        wire=[]
        if conversation_history:
            wire.extend(ChatMessage(x['role'],x['content']) for x in conversation_history[-24:])
        wire.append(ChatMessage('user',text))
        response=await asyncio.to_thread(
            provider.chat,wire,model=route.model,system=JARVIS_SYSTEM+self._runtime_context()+block
        )
        return {'kind':'chat','content':response.content,'provider':response.provider,'model':response.model,'mode':explicit_mode}


    async def _sync_connectors_for_personal_context(self):
        service=getattr(self.briefing,'connector_service',None) if self.briefing else None
        if service is None:
            return []
        try:
            return await service.sync_all()
        except Exception as exc:
            await self.bus.publish(Event(
                'connector.sync.personal_context_failed',severity='warning',
                payload={'error':str(exc)}
            ))
            return []

    def _runtime_context(self):
        if not self.briefing:
            return ''
        try:
            snap=self.briefing.snapshot()
            sources=snap.get('connectors',{}).get('sources',[])
            counts=snap.get('connectors',{}).get('counts',{})
            if not sources:
                return '\n\nESTADO REAL DE CONECTORES: nenhum connector registrado.'
            rows=[]
            for source in sources:
                rows.append(
                    f"{source.get('name') or source.get('connector_id')}: "
                    f"{source.get('status','unknown')}"
                )
            return (
                '\n\nESTADO REAL DE CONECTORES DO RUNTIME:\n- ' + '\n- '.join(rows) +
                f"\nItens sincronizados: {counts.get('total',0)}; não lidos: {counts.get('unread',0)}; eventos: {counts.get('events',0)}."
                '\nUse somente dados efetivamente sincronizados ao falar sobre fontes pessoais.'
            )
        except Exception:
            return '\n\nESTADO REAL DE CONECTORES: não foi possível consultar o snapshot agora.'

    @staticmethod
    def _with_history(text, history):
        rows=[]
        for item in history[-24:]:
            role=item.get('role','user')
            content=str(item.get('content','')).strip()
            if content:
                rows.append(f"{role.upper()}: {content}")
        return text + ("\n\nCONTEXTO DA CONVERSA ANTERIOR:\n" + "\n".join(rows) if rows else "")

    async def _delegate_agent(self,agent_id,title,objective,*,min_chars=40,conversation_history=None):
        task=await self.task_service.create(
            title,objective,metadata={'delegated_by':'jarvis','agent':agent_id}
        )
        await self.task_service.transition(task.task_id,TaskStatus.PLANNING)
        await self.bus.publish(Event(
            'agent.selected',task_id=task.task_id,agent_id=agent_id,
            payload={'reason':f'mission requires {agent_id}'}
        ))
        await self.task_service.transition(task.task_id,TaskStatus.READY)
        await self.task_service.transition(task.task_id,TaskStatus.RUNNING)
        agent=self.agent_registry.runtime(agent_id)
        try:
            context=self._with_history('', conversation_history or []) if conversation_history else ''
            result=await agent.run(objective,task_id=task.task_id,context=context)
            await self.task_service.transition(task.task_id,TaskStatus.VERIFYING)
            if not result.success or len(result.summary.strip())<min_chars:
                raise RuntimeError(f'{agent_id} produziu uma entrega insuficiente.')
            await self.bus.publish(Event(
                'verification.passed',task_id=task.task_id,agent_id=agent_id,
                payload={'artifact_id':result.artifact_id,'verification':'basic_artifact'}
            ))
            await self.task_service.transition(task.task_id,TaskStatus.COMPLETED)
            return {
                'kind':'delegated','agent':agent_id,'task_id':task.task_id,
                'content':result.summary,'artifact_id':result.artifact_id,
                'artifact_path':result.artifact_path,'metadata':result.metadata
            }
        except Exception as exc:
            current=self.task_service.tasks.get(task.task_id)
            if current.status not in {TaskStatus.FAILED,TaskStatus.COMPLETED,TaskStatus.CANCELLED}:
                try: await self.task_service.transition(task.task_id,TaskStatus.FAILED,error=str(exc))
                except Exception: pass
            raise

    async def _delegate_tool_plan(self,text):
        plan=await self.tool_planner.plan(text)
        if not plan.get('tool_id'):
            return {
                'kind':'tool_plan','agent':'jarvis',
                'content':'Nenhuma ferramenta disponível consegue executar essa ação com segurança.',
                'metadata':plan
            }
        operator=self.agent_registry.runtime('operations.operator')
        task=await self.task_service.create(
            'Ação planejada pelo Jarvis',text,
            metadata={
                'delegated_by':'jarvis','agent':'operations.operator',
                'tool_plan':plan
            }
        )
        await self.task_service.transition(task.task_id,TaskStatus.PLANNING)
        await self.bus.publish(Event(
            'tool.planned',task_id=task.task_id,agent_id='operations.operator',
            payload=plan
        ))
        await self.task_service.transition(task.task_id,TaskStatus.READY)
        await self.task_service.transition(task.task_id,TaskStatus.RUNNING)
        result=await operator.execute(
            plan['tool_id'],plan.get('payload') or {},task_id=task.task_id
        )
        status=result.metadata.get('status')
        if status=='approval_required':
            await self.task_service.transition(task.task_id,TaskStatus.BLOCKED)
            return {
                'kind':'approval_required','agent':'operations.operator',
                'task_id':task.task_id,'approval_id':result.metadata.get('approval_id'),
                'content':result.summary,'metadata':{**result.metadata,'plan':plan}
            }
        if result.success:
            await self.task_service.transition(task.task_id,TaskStatus.VERIFYING)
            await self.task_service.transition(task.task_id,TaskStatus.COMPLETED)
        else:
            await self.task_service.transition(
                task.task_id,TaskStatus.FAILED,error=result.summary
            )
        return {
            'kind':'operator','agent':'operations.operator',
            'task_id':task.task_id,'content':result.summary,
            'metadata':{**result.metadata,'plan':plan}
        }

    def _extract_after(self,text,prefixes):
        lowered=text.lower()
        for prefix in prefixes:
            index=lowered.find(prefix)
            if index>=0:
                return text[index+len(prefix):].strip(' :')
        return ''

    async def _delegate_operator(self,intent_name,text):
        operator=self.agent_registry.runtime('operations.operator')
        task=await self.task_service.create(
            'Ação operacional',text,
            metadata={'delegated_by':'jarvis','agent':'operations.operator'}
        )
        await self.task_service.transition(task.task_id,TaskStatus.PLANNING)
        await self.task_service.transition(task.task_id,TaskStatus.READY)
        await self.task_service.transition(task.task_id,TaskStatus.RUNNING)

        if intent_name=='operator_time':
            tool_id='system.time'; payload={}
        elif intent_name=='operator_list':
            path=self._extract_after(text,('liste a pasta','listar pasta'))
            tool_id='files.list_directory'; payload={'path':path}
        elif intent_name=='operator_read':
            path=self._extract_after(text,('leia o arquivo','ler arquivo'))
            tool_id='files.read_text'; payload={'path':path}
        elif intent_name=='operator_write':
            body=self._extract_after(text,('crie o arquivo','crie arquivo','escreva o arquivo','escreva arquivo'))
            if '::' not in body:
                await self.task_service.transition(
                    task.task_id,TaskStatus.FAILED,
                    error='Formato esperado: crie arquivo nome.txt :: conteúdo'
                )
                return {
                    'kind':'operator','agent':'operations.operator','task_id':task.task_id,
                    'content':'Use: crie arquivo nome.txt :: conteúdo',
                    'metadata':{'status':'failed'}
                }
            relative_path,content=body.split('::',1)
            tool_id='files.write_workspace_text'
            payload={'relative_path':relative_path.strip(),'content':content.strip()}
        elif intent_name=='operator_browser_open':
            url=self._extract_after(text,('abra o site','abra a url','abrir o site','abrir a url'))
            if not url.startswith(('http://','https://')):
                url='https://'+url
            tool_id='browser.open';payload={'url':url}
        elif intent_name=='operator_windows_list':
            tool_id='windows.list';payload={}
        elif intent_name=='operator_windows_activate':
            title=self._extract_after(text,('ative a janela','ativar a janela','abra a janela'))
            tool_id='windows.activate';payload={'window_title_re':f'.*{title}.*'}
        elif intent_name=='operator_whatsapp_send':
            body=self._extract_after(
                text,('envie uma mensagem no whatsapp para','mande uma mensagem no whatsapp para','whatsapp para')
            )
            if ':' not in body:
                await self.task_service.transition(
                    task.task_id,TaskStatus.FAILED,
                    error='Formato esperado: envie uma mensagem no WhatsApp para Nome: mensagem'
                )
                return {
                    'kind':'operator','agent':'operations.operator','task_id':task.task_id,
                    'content':'Use: envie uma mensagem no WhatsApp para Nome: mensagem',
                    'metadata':{'status':'failed'}
                }
            contact,message=body.split(':',1)
            tool_id='whatsapp.send_message'
            payload={'contact':contact.strip(),'message':message.strip()}
        else:
            raise RuntimeError(intent_name)

        result=await operator.execute(tool_id,payload,task_id=task.task_id)
        status=result.metadata.get('status')

        if status=='approval_required':
            await self.task_service.transition(task.task_id,TaskStatus.BLOCKED)
            return {
                'kind':'approval_required','agent':'operations.operator',
                'task_id':task.task_id,'content':result.summary,
                'approval_id':result.metadata.get('approval_id'),
                'metadata':result.metadata
            }

        if result.success:
            await self.task_service.transition(task.task_id,TaskStatus.VERIFYING)
            await self.bus.publish(Event(
                'verification.passed',task_id=task.task_id,agent_id='operations.operator',
                payload={'tool_id':tool_id,'evidence':result.metadata.get('evidence',{})}
            ))
            await self.task_service.transition(task.task_id,TaskStatus.COMPLETED)
        else:
            await self.task_service.transition(
                task.task_id,TaskStatus.FAILED,error=result.summary
            )

        return {
            'kind':'operator','agent':'operations.operator','task_id':task.task_id,
            'content':result.summary,'metadata':result.metadata
        }
