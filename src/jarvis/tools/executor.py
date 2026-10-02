from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from jarvis.core.events import Event
from jarvis.security import PolicyDecision


@dataclass(slots=True)
class ToolExecution:
    status:str
    tool_id:str
    task_id:str|None=None
    output:dict=field(default_factory=dict)
    evidence:dict=field(default_factory=dict)
    error:str|None=None
    approval_id:str|None=None
    tool_run_id:str|None=None

    @property
    def success(self):
        return self.status=='completed'


class ToolExecutor:
    def __init__(self,*,registry,policy,approvals,tool_runs,bus):
        self.registry=registry
        self.policy=policy
        self.approvals=approvals
        self.tool_runs=tool_runs
        self.bus=bus

    async def execute(self,tool_id,payload,*,task_id=None,approval_granted=False):
        tool=self.registry.get(tool_id)
        decision=self.policy.decide(tool.risk)

        if decision==PolicyDecision.BLOCK:
            await self.bus.publish(Event(
                'tool.blocked',severity='warning',task_id=task_id,
                payload={'tool_id':tool_id,'risk':str(tool.risk)}
            ))
            return ToolExecution('blocked',tool_id,task_id,error='A política atual bloqueia esta ação.')

        if decision==PolicyDecision.APPROVAL and not approval_granted:
            approval_id=self.approvals.request(
                task_id,tool_id,str(tool.risk),
                {'tool_id':tool_id,'payload':payload}
            )
            await self.bus.publish(Event(
                'approval.required',severity='warning',task_id=task_id,
                payload={'approval_id':approval_id,'tool_id':tool_id,'risk':str(tool.risk)}
            ))
            return ToolExecution(
                'approval_required',tool_id,task_id,
                approval_id=approval_id,
                error='Ação aguardando aprovação.'
            )

        run_id=self.tool_runs.start(task_id,tool_id,payload)
        await self.bus.publish(Event(
            'tool.started',task_id=task_id,
            payload={'tool_id':tool_id,'tool_run_id':run_id}
        ))
        try:
            result=await asyncio.to_thread(tool.execute,payload)
            if not result.success:
                self.tool_runs.finish(
                    run_id,status='failed',
                    output=result.output,evidence=result.evidence,error=result.error
                )
                await self.bus.publish(Event(
                    'tool.failed',severity='error',task_id=task_id,
                    payload={'tool_id':tool_id,'tool_run_id':run_id,'error':result.error}
                ))
                return ToolExecution(
                    'failed',tool_id,task_id,result.output,result.evidence,
                    result.error,tool_run_id=run_id
                )

            verified=await asyncio.to_thread(tool.verify,payload,result)
            if not verified.success:
                self.tool_runs.finish(
                    run_id,status='uncertain',
                    output=verified.output,evidence=verified.evidence,error=verified.error
                )
                await self.bus.publish(Event(
                    'verification.uncertain',severity='warning',task_id=task_id,
                    payload={'tool_id':tool_id,'tool_run_id':run_id,'error':verified.error}
                ))
                return ToolExecution(
                    'uncertain',tool_id,task_id,verified.output,verified.evidence,
                    verified.error,tool_run_id=run_id
                )

            self.tool_runs.finish(
                run_id,status='completed',
                output=verified.output,evidence=verified.evidence
            )
            await self.bus.publish(Event(
                'tool.completed',task_id=task_id,
                payload={'tool_id':tool_id,'tool_run_id':run_id,'evidence':verified.evidence}
            ))
            return ToolExecution(
                'completed',tool_id,task_id,verified.output,verified.evidence,
                tool_run_id=run_id
            )
        except Exception as exc:
            self.tool_runs.finish(run_id,status='failed',error=str(exc))
            await self.bus.publish(Event(
                'tool.failed',severity='error',task_id=task_id,
                payload={'tool_id':tool_id,'tool_run_id':run_id,'error':str(exc)}
            ))
            return ToolExecution(
                'failed',tool_id,task_id,error=str(exc),tool_run_id=run_id
            )

    async def execute_approved(self,approval_id):
        approval=self.approvals.get(approval_id)
        if not approval:
            raise KeyError(f'Aprovação inexistente: {approval_id}')
        if approval['status']!='pending':
            raise ValueError(f"Aprovação já está {approval['status']}.")
        request=approval.get('payload') or {}
        tool_id=request.get('tool_id')
        payload=request.get('payload') or {}
        result=await self.execute(
            tool_id,payload,task_id=approval.get('task_id'),approval_granted=True
        )
        self.approvals.resolve(approval_id,'approved')
        await self.bus.publish(Event(
            'approval.approved',task_id=approval.get('task_id'),
            payload={'approval_id':approval_id,'tool_id':tool_id,'result_status':result.status}
        ))
        return result

    async def reject(self,approval_id):
        approval=self.approvals.get(approval_id)
        if not approval:
            raise KeyError(f'Aprovação inexistente: {approval_id}')
        if approval['status']!='pending':
            raise ValueError(f"Aprovação já está {approval['status']}.")
        self.approvals.resolve(approval_id,'rejected')
        await self.bus.publish(Event(
            'approval.rejected',task_id=approval.get('task_id'),
            payload={'approval_id':approval_id,'action':approval.get('action')}
        ))
        return {'status':'rejected','approval_id':approval_id}
