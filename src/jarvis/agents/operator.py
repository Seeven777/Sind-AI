from __future__ import annotations

from jarvis.agents.base import AgentCard, AgentResult
from jarvis.core.events import Event
from jarvis.tasks import TaskStatus


class OperatorAgent:
    card=AgentCard(
        'operations.operator','Operator','Operations',
        'Executar ações reais usando ferramentas autorizadas e verificar o resultado.',
        ('execution','tool_use','verification'),
        (
            'system.time','files.read_text','files.list_directory','files.write_workspace_text','files.write_workspace_pdf',
            'web.search','web.fetch','browser.open','browser.snapshot','browser.fill',
            'browser.click','windows.list','windows.inspect','windows.activate',
            'windows.set_text','windows.click','whatsapp.send_message'
        ),
        'tool_use',True,
    )

    def __init__(self,*,tool_executor,agent_runs,bus,task_service,goal_verifier=None,model_router=None):
        self.tool_executor=tool_executor
        self.agent_runs=agent_runs
        self.bus=bus
        self.task_service=task_service
        self.goal_verifier=goal_verifier
        self.model_router=model_router

    async def execute(self,tool_id,payload,*,task_id):
        assigned=self.model_router.local_model(self.card.model_capability) if self.model_router else None
        rid=self.agent_runs.start(
            self.card.agent_id,task_id,assigned,
            {'tool_id':tool_id,'payload':payload}
        )
        self.agent_runs.update_activity(rid,f'Executando {tool_id}',0.25)
        await self.bus.publish(Event(
            'agent.started',task_id=task_id,agent_id=self.card.agent_id,
            payload={'agent_run_id':rid,'activity':f'Executando {tool_id}','model':assigned}
        ))
        result=await self.tool_executor.execute(tool_id,payload,task_id=task_id)

        if result.status=='approval_required':
            self.agent_runs.update_activity(rid,'Aguardando sua aprovação',0.45)
            await self.bus.publish(Event(
                'agent.progress',task_id=task_id,agent_id=self.card.agent_id,
                payload={'agent_run_id':rid,'progress':0.45,'activity':'Aguardando sua aprovação'}
            ))
            return AgentResult(
                False,
                f'A ação {tool_id} precisa da sua aprovação antes de ser executada.',
                metadata={'status':result.status,'approval_id':result.approval_id,'agent_run_id':rid}
            )

        if result.success:
            verification=None
            if self.goal_verifier is not None:
                expected=self._expected_for(tool_id,result)
                verification=self.goal_verifier.verify(
                    expected,{**result.output,**result.evidence}
                ) if expected else None
                if verification is not None and not verification.passed:
                    self.agent_runs.finish(rid,error=verification.error or verification.status)
                    await self.bus.publish(Event(
                        'verification.failed',severity='error',task_id=task_id,
                        agent_id=self.card.agent_id,
                        payload={
                            'agent_run_id':rid,'tool_id':tool_id,
                            'error':verification.error,'evidence':verification.evidence
                        }
                    ))
                    return AgentResult(
                        False,verification.error or 'Verificação independente falhou.',
                        metadata={
                            'status':verification.status,'output':result.output,
                            'evidence':verification.evidence,'agent_run_id':rid
                        }
                    )

            self.agent_runs.finish(rid)
            await self.bus.publish(Event(
                'verification.passed',task_id=task_id,agent_id=self.card.agent_id,
                payload={
                    'agent_run_id':rid,'tool_id':tool_id,
                    'evidence':verification.evidence if verification else result.evidence
                }
            ))
            await self.bus.publish(Event(
                'agent.completed',task_id=task_id,agent_id=self.card.agent_id,
                payload={'agent_run_id':rid,'tool_id':tool_id,'evidence':result.evidence}
            ))
            return AgentResult(
                True,self._summary(tool_id,result.output,result.evidence),
                metadata={
                    'status':result.status,'output':result.output,'evidence':result.evidence,
                    'goal_verification':{
                        'status':verification.status,'passed':verification.passed,
                        'evidence':verification.evidence
                    } if verification else None,
                    'agent_run_id':rid
                }
            )

        self.agent_runs.finish(rid,error=result.error or result.status)
        await self.bus.publish(Event(
            'agent.failed',severity='error',task_id=task_id,agent_id=self.card.agent_id,
            payload={'agent_run_id':rid,'tool_id':tool_id,'error':result.error or result.status}
        ))
        return AgentResult(
            False,result.error or f'Falha em {tool_id}.',
            metadata={'status':result.status,'output':result.output,'evidence':result.evidence,'agent_run_id':rid}
        )

    async def run(self, objective, *, task_id, context=""):
        """Execute an optional machine-readable execution plan.

        Operator remains the sole authority for physical/external actions.
        An empty/no plan is a valid no-op for complex knowledge-only missions.
        """
        import json
        import re

        plan = None
        match = re.search(r"EXECUTION_PLAN:\s*```(?:json)?\s*(\{.*?\})\s*```", context, re.S)
        if not match:
            match = re.search(r"EXECUTION_PLAN:\s*(\{.*\})", context, re.S)
        if match:
            try:
                plan = json.loads(match.group(1))
            except json.JSONDecodeError:
                plan = None

        if plan is None:
            return AgentResult(
                True,
                'Operator não recebeu um plano de execução verificável; nenhuma ação física foi iniciada.',
                metadata={'status': 'no_execution_plan', 'actions_executed': 0},
            )

        actions = plan.get('actions') if isinstance(plan, dict) else None
        if not isinstance(actions, list):
            return AgentResult(
                False,
                'EXECUTION_PLAN inválido: actions precisa ser uma lista.',
                metadata={'status': 'invalid_execution_plan'},
            )

        executed = []
        for index, action in enumerate(actions, 1):
            if not isinstance(action, dict) or not action.get('tool_id'):
                return AgentResult(
                    False,
                    f'EXECUTION_PLAN inválido na ação {index}.',
                    metadata={'status': 'invalid_execution_plan', 'action': index},
                )
            result = await self.execute(
                str(action['tool_id']), action.get('payload') or {}, task_id=task_id
            )
            executed.append({
                'index': index,
                'tool_id': action['tool_id'],
                'success': result.success,
                'status': result.metadata.get('status'),
                'evidence': result.metadata.get('evidence', {}),
            })
            if not result.success:
                return AgentResult(
                    False,
                    result.summary,
                    metadata={
                        'status': result.metadata.get('status', 'failed'),
                        'actions_executed': len(executed),
                        'actions': executed,
                        'approval_id': result.metadata.get('approval_id'),
                    },
                )

        return AgentResult(
            True,
            f'Operator concluiu {len(executed)} ação(ões) e recebeu evidência de execução.',
            metadata={'status': 'completed', 'actions_executed': len(executed), 'actions': executed},
        )

    async def resume_approval(self,approval_id):
        approval=self.tool_executor.approvals.get(approval_id)
        if not approval:
            raise KeyError(approval_id)
        task_id=approval.get('task_id')
        result=await self.tool_executor.execute_approved(approval_id)
        if task_id:
            current=self.task_service.tasks.get(task_id)
            if current.status==TaskStatus.BLOCKED:
                # A team mission has remaining pipeline stages (especially the
                # independent Reviewer). Tool verification alone must not turn
                # that mission into a successful task.
                if current.metadata.get('mode')=='team':
                    await self.bus.publish(Event(
                        'mission.resume_required',severity='warning',task_id=task_id,
                        agent_id=self.card.agent_id,
                        payload={
                            'approval_id':approval_id,'tool_id':result.tool_id,
                            'tool_status':result.status,
                            'reason':'A missão em equipe requer retomada pelo orquestrador e revisão final.',
                        },
                    ))
                    return {
                        'status':result.status,'tool_id':result.tool_id,'task_id':task_id,
                        'output':result.output,'evidence':result.evidence,'error':result.error,
                        'mission_resume_required':True,
                    }
                await self.task_service.transition(task_id,TaskStatus.READY)
                await self.task_service.transition(task_id,TaskStatus.RUNNING)
                if result.success:
                    await self.task_service.transition(task_id,TaskStatus.VERIFYING)
                    await self.task_service.transition(task_id,TaskStatus.COMPLETED)
                else:
                    await self.task_service.transition(task_id,TaskStatus.FAILED,error=result.error or result.status)
        return {
            'status':result.status,'tool_id':result.tool_id,'task_id':task_id,
            'output':result.output,'evidence':result.evidence,'error':result.error
        }

    async def reject_approval(self,approval_id):
        approval=self.tool_executor.approvals.get(approval_id)
        if not approval: raise KeyError(approval_id)
        task_id=approval.get('task_id')
        result=await self.tool_executor.reject(approval_id)
        if task_id:
            current=self.task_service.tasks.get(task_id)
            if current.status==TaskStatus.BLOCKED:
                await self.task_service.transition(task_id,TaskStatus.CANCELLED)
        return result

    def _expected_for(self,tool_id,result):
        if tool_id=='files.write_workspace_text':
            return {
                'kind':'file_sha256',
                'path':result.output.get('path'),
                'sha256':result.evidence.get('sha256')
            }
        if tool_id=='files.write_workspace_pdf':
            return {
                'kind':'file_sha256',
                'path':result.output.get('path'),
                'sha256':result.evidence.get('sha256')
            }
        if tool_id in {'files.read_text','files.list_directory'}:
            return {'kind':'evidence_key','key':'exists'}
        if tool_id=='system.time':
            return {'kind':'evidence_key','key':'source'}
        if tool_id.startswith('browser.'):
            return {'kind':'evidence_key','key':next(iter(result.evidence.keys()),'')}
        if tool_id.startswith('windows.'):
            return {'kind':'evidence_key','key':next(iter(result.evidence.keys()),'')}
        if tool_id=='whatsapp.send_message':
            return {'kind':'evidence_key','key':'verified_in_ui'}
        return None

    def _summary(self,tool_id,output,evidence):
        if tool_id=='system.time':
            return f"Horário UTC confirmado pelo relógio do sistema: {output.get('utc')}."
        if tool_id=='files.list_directory':
            names=[x['name'] for x in output.get('entries',[])[:30]]
            return (
                f"Pasta confirmada: {output.get('path')}\n"
                f"{output.get('count',0)} itens retornados:\n- " + "\n- ".join(names)
            )
        if tool_id=='files.read_text':
            return (
                f"Arquivo confirmado: {output.get('path')}\n\n"
                f"{output.get('content','')}"
            )
        if tool_id=='files.write_workspace_text':
            return (
                f"Arquivo criado e verificado no workspace do Jarvis:\n"
                f"{output.get('path')}\nSHA-256: {evidence.get('sha256')}"
            )
        if tool_id=='files.write_workspace_pdf':
            return (
                f"PDF criado e verificado no workspace do Jarvis:\n"
                f"{output.get('path')}\n"
                f"Páginas: {evidence.get('pages', output.get('pages','—'))}\n"
                f"SHA-256: {evidence.get('sha256')}"
            )
        if tool_id=='web.search':
            lines=[f"Resultados para: {output.get('query')}"]
            for item in output.get('results',[])[:10]:
                lines.append(f"- {item.get('title')} — {item.get('url')}")
            return '\n'.join(lines)
        if tool_id=='web.fetch':
            return f"{output.get('title') or output.get('url')}\n\n{output.get('content','')}"
        if tool_id=='browser.open':
            return f"Navegador abriu: {output.get('url')} — {output.get('title','')}"
        if tool_id=='browser.snapshot':
            return f"{output.get('title','')}\n{output.get('url','')}\n\n{output.get('text','')}"
        if tool_id=='windows.list':
            return '\n'.join(
                f"- {x.get('title')}" for x in output.get('windows',[])
            ) or 'Nenhuma janela observada.'
        if tool_id=='whatsapp.send_message':
            if output.get('verified'):
                return f"Mensagem enviada e verificada no WhatsApp para {output.get('contact')}."
            return 'Envio do WhatsApp não pôde ser verificado.'
        if tool_id.startswith('windows.') or tool_id.startswith('browser.'):
            return str(output)
        return str(output)
