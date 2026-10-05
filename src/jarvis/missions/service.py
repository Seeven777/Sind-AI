from __future__ import annotations
import json
import re
from jarvis.core.events import Event
from jarvis.tasks import TaskStatus
from .planner import MissionPlanner, MissionPlan

class MissionBlocked(RuntimeError):
    pass

class TeamMissionService:
    def __init__(self,*,agent_registry,task_service,missions,bus,workspace_id,planner=None):
        self.agent_registry=agent_registry; self.task_service=task_service; self.missions=missions; self.bus=bus; self.workspace_id=workspace_id; self.planner=planner or MissionPlanner()
    async def run(self,objective:str,*,title:str='Missão em equipe'):
        return await self.run_plan(objective,plan=self.planner.build(objective),title=title)
    async def run_with_agents(self,objective:str,*,agents,title='Missão especializada',reason='explicit specialist team'):
        pipeline=[]
        for agent_id in agents:
            if agent_id and agent_id not in pipeline:pipeline.append(agent_id)
        if not pipeline:raise RuntimeError('Equipe explícita vazia.')
        if pipeline[-1]!='review.verifier':pipeline.append('review.verifier')
        return await self.run_plan(objective,plan=MissionPlan(tuple(pipeline),reason),title=title)
    @staticmethod
    def _creator_gate(content):
        m=re.search(r'CREATOR_GATE:\s*(APPROVED|BLOCKED)',content.upper()); return m.group(1) if m else 'MISSING'
    @staticmethod
    def _developer_execution_plan(content):
        m=re.search(r'EXECUTION_PLAN:\s*```(?:json)?\s*(\{.*?\})\s*```',content,re.S) or re.search(r'EXECUTION_PLAN:\s*(\{.*\})',content,re.S)
        if not m:return None
        try:return json.loads(m.group(1))
        except json.JSONDecodeError:return None
    def _stage_context(self,plan,agent_id,context):
        if plan.mode!='complex':return context
        directives={
            'memory.curator':'STAGE DIRECTIVE: Memory Curator é o primeiro estágio. Recupere contexto histórico relevante e o estado atual para os próximos agentes.',
            'research.general':'STAGE DIRECTIVE: Research em missão complexa. Use somente o contexto e fontes disponibilizadas pelo sistema. Não faça chamadas externas nem acesse redes sociais ou serviços não autorizados.',
            'intelligence.analyst':'STAGE DIRECTIVE: Analyst deve transformar evidência em decisões, riscos, prioridades e lacunas.',
            'creative.creator':'STAGE DIRECTIVE: Creator é GATE de política antes do Developer. Marque CREATOR_GATE: APPROVED somente se o plano estiver alinhado às políticas; caso contrário BLOCKED.',
            'engineering.developer':'STAGE DIRECTIVE: Developer só trabalha após Creator Gate APPROVED. Produza implementação concreta, testes e, quando houver ação operacional posterior, EXECUTION_PLAN em JSON. Não execute ações físicas diretamente.',
            'operations.operator':'STAGE DIRECTIVE: Operator é a única autoridade para ações físicas/externas. Execute somente EXECUTION_PLAN pelas ferramentas registradas e com evidência verificável. Sem plano, faça no-op explícito.',
            'review.verifier':'STAGE DIRECTIVE: Reviewer é o gate final independente. Verifique todos os artifacts e evidências, inclusive execução do Operator quando existir.',
        }
        prefix=directives.get(agent_id,'')
        return prefix+('\n\n'+context if context else '')
    async def run_plan(self,objective:str,*,plan:MissionPlan,title:str):
        pipeline=plan.agents
        if not pipeline:raise RuntimeError('Mission planner retornou equipe vazia.')
        available={c.agent_id for c in self.agent_registry.available()}
        missing=[x for x in pipeline if x not in available]
        if missing:raise RuntimeError('Agentes indisponíveis: '+', '.join(missing))
        task=await self.task_service.create(title,objective,metadata={'mode':'team','pipeline':list(pipeline),'workspace_id':self.workspace_id,'plan_reason':plan.reason,'mission_mode':plan.mode,'research_external_allowed':plan.research_external_allowed,'creator_gate_required':plan.creator_gate_required,'operator_required':plan.operator_required})
        await self.task_service.transition(task.task_id,TaskStatus.PLANNING)
        mission_id=self.missions.create(task.task_id,title,objective,self.workspace_id,{'pipeline':list(pipeline),'plan_reason':plan.reason,'mission_mode':plan.mode,'research_external_allowed':plan.research_external_allowed,'creator_gate_required':plan.creator_gate_required,'operator_required':plan.operator_required})
        step_ids=[self.missions.add_step(mission_id,i,a,metadata={'plan_reason':plan.reason,'mission_mode':plan.mode}) for i,a in enumerate(pipeline,1)]
        await self.bus.publish(Event('mission.created',task_id=task.task_id,payload={'mission_id':mission_id,'pipeline':list(pipeline),'title':title,'plan_reason':plan.reason,'mission_mode':plan.mode}))
        await self.task_service.transition(task.task_id,TaskStatus.READY); await self.task_service.transition(task.task_id,TaskStatus.RUNNING)
        context=''; artifacts=[]
        try:
            for index,agent_id in enumerate(pipeline,1):
                step_id=step_ids[index-1]; self.missions.start_step(step_id)
                await self.bus.publish(Event('mission.step.started',task_id=task.task_id,agent_id=agent_id,payload={'mission_id':mission_id,'step_id':step_id,'sequence':index}))
                agent=self.agent_registry.runtime(agent_id); stage_context=self._stage_context(plan,agent_id,context)
                if plan.mode=='complex' and agent_id=='research.general':
                    result=await agent.run(objective,task_id=task.task_id,context=stage_context,allow_external=plan.research_external_allowed)
                else:
                    result=await agent.run(objective,task_id=task.task_id,context=stage_context)
                if not result.success:
                    self.missions.finish_step(step_id,result.artifact_id,error=result.summary)
                    if result.metadata.get('status')=='approval_required':
                        await self.task_service.transition(task.task_id,TaskStatus.BLOCKED)
                        await self.bus.publish(Event('mission.blocked',severity='warning',task_id=task.task_id,agent_id=agent_id,payload={'mission_id':mission_id,'approval_id':result.metadata.get('approval_id'),'reason':result.summary}))
                        return {'kind':'team_mission_blocked','mission_id':mission_id,'task_id':task.task_id,'agents':list(pipeline),'plan_reason':plan.reason,'content':result.summary,'review':'','review_passed':False,'artifacts':artifacts,'approval_id':result.metadata.get('approval_id')}
                    raise RuntimeError(result.summary)
                if plan.mode=='complex' and plan.creator_gate_required and agent_id=='creative.creator':
                    gate=self._creator_gate(result.summary)
                    if gate!='APPROVED':
                        self.missions.finish_step(step_id,result.artifact_id,error=f'Creator gate: {gate}')
                        await self.task_service.transition(task.task_id,TaskStatus.FAILED,error=f'Creator gate: {gate}')
                        raise RuntimeError('Creator não aprovou o plano antes do Developer. A missão foi interrompida por política.')
                artifact={'agent_id':agent_id,'artifact_id':result.artifact_id,'artifact_path':result.artifact_path,'content':result.summary,'metadata':result.metadata}
                if agent_id=='engineering.developer' and plan.mode=='complex':
                    execution_plan=self._developer_execution_plan(result.summary)
                    artifact['metadata']={**result.metadata,'execution_plan':execution_plan}
                    if plan.operator_required and execution_plan is None:
                        self.missions.finish_step(step_id,result.artifact_id,error='Developer não produziu EXECUTION_PLAN válido.')
                        await self.task_service.transition(task.task_id,TaskStatus.FAILED,error='Developer não produziu EXECUTION_PLAN válido.')
                        raise RuntimeError('A missão requer execução operacional, mas o Developer não produziu um plano de execução verificável.')
                artifacts.append(artifact); self.missions.finish_step(step_id,result.artifact_id)
                next_agent=pipeline[index] if index<len(pipeline) else None
                await self.bus.publish(Event('mission.handoff',task_id=task.task_id,agent_id=agent_id,payload={'mission_id':mission_id,'from_agent':agent_id,'to_agent':next_agent,'artifact_id':result.artifact_id}))
                context=result.summary
            await self.task_service.transition(task.task_id,TaskStatus.VERIFYING)
            review=artifacts[-1]['content']
            if artifacts[-1]['agent_id']!='review.verifier':raise RuntimeError('Missão terminou sem Reviewer.')
            passed='VERDICT: PASS' in review.upper()
            await self.bus.publish(Event('verification.passed' if passed else 'verification.uncertain',severity=None if passed else 'warning',task_id=task.task_id,agent_id='review.verifier',payload={'mission_id':mission_id,'verdict':'PASS' if passed else 'REVISE','review_artifact_id':artifacts[-1]['artifact_id']}))
            delivery=next((item for item in reversed(artifacts[:-1]) if item.get('artifact_path') or item.get('artifact_id')), artifacts[-1])
            await self.task_service.transition(task.task_id,TaskStatus.COMPLETED); self.missions.complete(mission_id)
            await self.bus.publish(Event('mission.completed',task_id=task.task_id,payload={'mission_id':mission_id,'artifacts':[a['artifact_id'] for a in artifacts],'review_passed':passed,'mission_mode':plan.mode}))
            return {'kind':'team_mission','mission_id':mission_id,'task_id':task.task_id,'agents':list(pipeline),'plan_reason':plan.reason,'mission_mode':plan.mode,'content':delivery['content'],'review':review,'review_passed':passed,'artifacts':artifacts,'artifact_id':delivery['artifact_id'],'artifact_path':delivery['artifact_path']}
        except Exception as exc:
            current=self.task_service.tasks.get(task.task_id)
            if current.status not in {TaskStatus.FAILED,TaskStatus.COMPLETED,TaskStatus.CANCELLED,TaskStatus.BLOCKED}:
                try:await self.task_service.transition(task.task_id,TaskStatus.FAILED,error=str(exc))
                except Exception:pass
            self.missions.complete(mission_id,error=str(exc))
            await self.bus.publish(Event('mission.failed',severity='error',task_id=task.task_id,payload={'mission_id':mission_id,'error':str(exc)}))
            raise
