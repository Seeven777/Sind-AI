import asyncio
from pathlib import Path

from jarvis.app.product_runtime import start_product_runtime
from jarvis.models import MockModelProvider
from jarvis.tasks import TaskStatus


def test_operator_executes_read_tool_and_verifies(tmp_path: Path):
    async def scenario():
        target=tmp_path/'sample.txt'
        target.write_text('conteudo confirmado',encoding='utf-8')
        rt=await start_product_runtime(tmp_path/'data',model_provider=MockModelProvider())
        try:
            result=await rt.orchestrator.handle(f'Leia o arquivo {target}')
            assert result['kind']=='operator'
            assert result['metadata']['status']=='completed'
            assert result['metadata']['evidence']['exists'] is True
            assert 'conteudo confirmado' in result['content']
            assert rt.foundation.tasks.get(result['task_id']).status==TaskStatus.COMPLETED
        finally:
            await rt.close()
    asyncio.run(scenario())


def test_operator_write_requires_approval_then_executes(tmp_path: Path):
    async def scenario():
        rt=await start_product_runtime(tmp_path/'data',model_provider=MockModelProvider())
        try:
            result=await rt.orchestrator.handle('Crie arquivo notas/teste.txt :: conteúdo aprovado')
            assert result['kind']=='approval_required'
            approval_id=result['approval_id']
            assert approval_id
            assert rt.foundation.tasks.get(result['task_id']).status==TaskStatus.BLOCKED

            operator=rt.agent_registry.runtime('operations.operator')
            executed=await operator.resume_approval(approval_id)
            assert executed['status']=='completed'
            assert Path(executed['output']['path']).read_text(encoding='utf-8')=='conteúdo aprovado'
            assert rt.foundation.tasks.get(result['task_id']).status==TaskStatus.COMPLETED
        finally:
            await rt.close()
    asyncio.run(scenario())


def test_team_approval_does_not_complete_before_mission_review(tmp_path: Path):
    async def scenario():
        rt = await start_product_runtime(tmp_path / 'data', model_provider=MockModelProvider())
        try:
            task = await rt.foundation.task_service.create(
                'Missão em equipe', 'Executar ação pendente', metadata={'mode': 'team'}
            )
            await rt.foundation.task_service.transition(task.task_id, TaskStatus.PLANNING)
            await rt.foundation.task_service.transition(task.task_id, TaskStatus.READY)
            await rt.foundation.task_service.transition(task.task_id, TaskStatus.RUNNING)
            await rt.foundation.task_service.transition(task.task_id, TaskStatus.BLOCKED)
            pending = await rt.tool_executor.execute(
                'files.write_workspace_text',
                {'relative_path': 'team/pending.txt', 'content': 'verificado'},
                task_id=task.task_id,
            )
            assert pending.status == 'approval_required'

            operator = rt.agent_registry.runtime('operations.operator')
            resumed = await operator.resume_approval(pending.approval_id)
            assert resumed['status'] == 'completed'
            assert resumed['mission_resume_required'] is True
            assert rt.foundation.tasks.get(task.task_id).status == TaskStatus.BLOCKED
        finally:
            await rt.close()

    asyncio.run(scenario())
