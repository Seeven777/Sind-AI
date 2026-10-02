from __future__ import annotations

from jarvis.core.events import Event
from jarvis.tasks import TaskStatus
from .planner import MissionPlanner, MissionPlan


class TeamMissionService:
    """Durable multi-agent mission with dynamic team assembly and handoffs."""

    def __init__(
        self,*,agent_registry,task_service,missions,bus,workspace_id,planner=None
    ):
        self.agent_registry=agent_registry
        self.task_service=task_service
        self.missions=missions
        self.bus=bus
        self.workspace_id=workspace_id
        self.planner=planner or MissionPlanner()

    async def run(self,objective:str,*,title:str='Missão em equipe')->dict:
        plan=self.planner.build(objective)
        return await self.run_plan(objective,plan=plan,title=title)

    async def run_with_agents(
        self,objective:str,*,agents,title:str='Missão especializada',reason:str='explicit specialist team'
    )->dict:
        pipeline=[]
        for agent_id in agents:
            if agent_id and agent_id not in pipeline:
                pipeline.append(agent_id)
        if not pipeline:
            raise RuntimeError('Equipe explícita vazia.')
        if pipeline[-1] != 'review.verifier':
            pipeline.append('review.verifier')
        return await self.run_plan(
            objective,
            plan=MissionPlan(tuple(pipeline),reason),
            title=title,
        )

    async def run_plan(self,objective:str,*,plan:MissionPlan,title:str)->dict:
        pipeline=plan.agents
        if not pipeline:
            raise RuntimeError('Mission planner retornou equipe vazia.')

        available_ids={c.agent_id for c in self.agent_registry.available()}
        unavailable=[agent_id for agent_id in pipeline if agent_id not in available_ids]
        if unavailable:
            raise RuntimeError(f'Agentes indisponíveis: {", ".join(unavailable)}')

        task=await self.task_service.create(
            title,objective,
            metadata={
                'mode':'team','pipeline':list(pipeline),
                'workspace_id':self.workspace_id,'plan_reason':plan.reason,
            }
        )
        await self.task_service.transition(task.task_id,TaskStatus.PLANNING)
        mission_id=self.missions.create(
            task.task_id,title,objective,self.workspace_id,
            {'pipeline':list(pipeline),'plan_reason':plan.reason}
        )
        step_ids=[]
        for index,agent_id in enumerate(pipeline,1):
            step_ids.append(self.missions.add_step(
                mission_id,index,agent_id,
                metadata={'plan_reason':plan.reason}
            ))
        await self.bus.publish(Event(
            'mission.created',task_id=task.task_id,
            payload={
                'mission_id':mission_id,'pipeline':list(pipeline),
                'title':title,'plan_reason':plan.reason
            }
        ))
        await self.task_service.transition(task.task_id,TaskStatus.READY)
        await self.task_service.transition(task.task_id,TaskStatus.RUNNING)

        context=''
        artifacts=[]
        try:
            for index,agent_id in enumerate(pipeline,1):
                step_id=step_ids[index-1]
                self.missions.start_step(step_id)
                await self.bus.publish(Event(
                    'mission.step.started',task_id=task.task_id,agent_id=agent_id,
                    payload={
                        'mission_id':mission_id,'step_id':step_id,'sequence':index
                    }
                ))
                agent=self.agent_registry.runtime(agent_id)
                result=await agent.run(
                    objective,task_id=task.task_id,context=context
                )
                artifacts.append({
                    'agent_id':agent_id,
                    'artifact_id':result.artifact_id,
                    'artifact_path':result.artifact_path,
                    'content':result.summary,
                })
                self.missions.finish_step(step_id,result.artifact_id)
                next_agent=pipeline[index] if index<len(pipeline) else None
                await self.bus.publish(Event(
                    'mission.handoff',task_id=task.task_id,agent_id=agent_id,
                    payload={
                        'mission_id':mission_id,'from_agent':agent_id,
                        'to_agent':next_agent,'artifact_id':result.artifact_id
                    }
                ))
                context=result.summary

            await self.task_service.transition(task.task_id,TaskStatus.VERIFYING)
            review=artifacts[-1]['content']
            if artifacts[-1]['agent_id']!='review.verifier':
                raise RuntimeError('Missão terminou sem Reviewer.')
            passed='VERDICT: PASS' in review.upper()
            if not passed:
                await self.bus.publish(Event(
                    'verification.uncertain',severity='warning',
                    task_id=task.task_id,agent_id='review.verifier',
                    payload={
                        'mission_id':mission_id,
                        'review_artifact_id':artifacts[-1]['artifact_id'],
                        'reason':'Reviewer não retornou VERDICT: PASS'
                    }
                ))
            else:
                await self.bus.publish(Event(
                    'verification.passed',task_id=task.task_id,
                    agent_id='review.verifier',
                    payload={
                        'mission_id':mission_id,'verdict':'PASS',
                        'review_artifact_id':artifacts[-1]['artifact_id']
                    }
                ))

            # Review is evidence, not the user-facing delivery.
            delivery=artifacts[-2] if len(artifacts)>=2 else artifacts[-1]
            await self.task_service.transition(task.task_id,TaskStatus.COMPLETED)
            self.missions.complete(mission_id)
            await self.bus.publish(Event(
                'mission.completed',task_id=task.task_id,
                payload={
                    'mission_id':mission_id,
                    'artifacts':[a['artifact_id'] for a in artifacts],
                    'review_passed':passed,
                }
            ))
            return {
                'kind':'team_mission','mission_id':mission_id,
                'task_id':task.task_id,'agents':list(pipeline),
                'plan_reason':plan.reason,
                'content':delivery['content'],'review':review,
                'review_passed':passed,'artifacts':artifacts,
                'artifact_id':delivery['artifact_id'],
                'artifact_path':delivery['artifact_path'],
            }
        except Exception as exc:
            current=self.task_service.tasks.get(task.task_id)
            if current.status not in {
                TaskStatus.FAILED,TaskStatus.COMPLETED,TaskStatus.CANCELLED
            }:
                try:
                    await self.task_service.transition(
                        task.task_id,TaskStatus.FAILED,error=str(exc)
                    )
                except Exception:
                    pass
            self.missions.complete(mission_id,error=str(exc))
            await self.bus.publish(Event(
                'mission.failed',severity='error',task_id=task.task_id,
                payload={'mission_id':mission_id,'error':str(exc)}
            ))
            raise
