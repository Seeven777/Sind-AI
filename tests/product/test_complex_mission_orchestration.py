from __future__ import annotations

import asyncio
from pathlib import Path

from jarvis.app.product_runtime import start_product_runtime
from jarvis.models import MockModelProvider
from jarvis.missions import MissionPlanner
from jarvis.tasks import TaskStatus


def test_complex_planner_matches_control_contract():
    plan = MissionPlanner().build(
        'Orquestre uma missão complexa ponta a ponta para analisar, desenvolver e executar o projeto.'
    )
    assert plan.mode == 'complex'
    assert plan.research_external_allowed is False
    assert plan.creator_gate_required is True
    assert plan.operator_required is True
    assert plan.agents == (
        'memory.curator',
        'research.general',
        'intelligence.analyst',
        'creative.creator',
        'engineering.developer',
        'operations.operator',
        'review.verifier',
    )


class ComplexSequenceProvider(MockModelProvider):
    def __init__(self):
        super().__init__('unused')
        self.calls = 0

    def chat(self, messages, *, model=None, system=None):
        self.calls += 1
        texts = {
            1: '# Pesquisa\n\nSomente contexto interno; nenhuma fonte externa foi consultada.',
            2: '# Análise\n\nPrioridades, riscos e decisões para execução.',
            3: '# Creator\n\nPlano alinhado à política e pronto para implementação.\n\nCREATOR_GATE: APPROVED\nREQUIRED_APPROVALS: nenhuma',
            4: '# Developer\n\nImplementação proposta com testes.\n\nEXECUTION_PLAN:\n```json\n{"actions": []}\n```',
            5: '# Review\n\nTodos os estágios estão coerentes e nenhuma ação não verificada foi declarada.\n\nVERDICT: PASS',
        }
        from jarvis.models.base import ModelResponse
        return ModelResponse(texts[self.calls], model or 'mock-model', 'mock')


def test_complex_mission_runs_full_control_pipeline(tmp_path: Path):
    async def run():
        provider = ComplexSequenceProvider()
        rt = await start_product_runtime(tmp_path, model_provider=provider)
        try:
            result = await rt.missions.run(
                'Orquestre uma missão complexa ponta a ponta para analisar, desenvolver e executar o projeto.'
            )
            assert result['mission_mode'] == 'complex'
            assert result['agents'] == [
                'memory.curator', 'research.general', 'intelligence.analyst',
                'creative.creator', 'engineering.developer', 'operations.operator',
                'review.verifier'
            ]
            assert provider.calls == 5
            assert result['review_passed'] is True
            assert rt.foundation.tasks.get(result['task_id']).status == TaskStatus.COMPLETED
            snap = rt.hq.snapshot()
            mission = next(m for m in snap['missions'] if m['mission_id'] == result['mission_id'])
            assert [s['status'] for s in mission['steps']] == ['completed'] * 7
            assert Path(result['artifact_path']).exists()
        finally:
            await rt.close()

    asyncio.run(run())


def test_creator_gate_blocks_developer(tmp_path: Path):
    class BlockProvider(MockModelProvider):
        def __init__(self): super().__init__('unused'); self.calls=0
        def chat(self, messages, *, model=None, system=None):
            self.calls += 1
            outputs = {
                1: '# Pesquisa\n\nEvidência interna suficiente para a missão, cobrindo o contexto operacional relevante e as premissas.',
                2: '# Análise\n\nRiscos, prioridades e decisões identificados com evidência suficiente para a próxima etapa.',
                3: '# Creator\n\nPlano bloqueado por política.\n\nCREATOR_GATE: BLOCKED\nREQUIRED_APPROVALS: aprovação humana necessária',
            }
            from jarvis.models.base import ModelResponse
            return ModelResponse(outputs[self.calls], model or 'mock-model', 'mock')
    async def run():
        provider=BlockProvider()
        rt=await start_product_runtime(tmp_path,model_provider=provider)
        try:
            try:
                await rt.missions.run('Orquestre uma missão complexa ponta a ponta para configurar o projeto.')
            except RuntimeError as exc:
                assert 'Creator não aprovou' in str(exc)
            else:
                raise AssertionError('A missão deveria ter sido bloqueada pelo Creator.')
            assert provider.calls == 3
        finally: await rt.close()
    asyncio.run(run())


def test_execution_required_needs_developer_plan(tmp_path: Path):
    class NoPlanProvider(MockModelProvider):
        def __init__(self): super().__init__('unused'); self.calls=0
        def chat(self, messages, *, model=None, system=None):
            self.calls += 1
            outputs = {
                1: '# Pesquisa\n\nEvidência interna suficiente para sustentar a decisão e orientar a execução sem fontes externas.',
                2: '# Análise\n\nPrioridades, riscos e decisões definidas para orientar a implementação com segurança.',
                3: '# Creator\n\nPlano aprovado.\n\nCREATOR_GATE: APPROVED\nREQUIRED_APPROVALS: nenhuma',
                4: '# Developer\n\nImplementação proposta sem plano operacional estruturado.',
            }
            from jarvis.models.base import ModelResponse
            return ModelResponse(outputs[self.calls], model or 'mock-model', 'mock')
    async def run():
        provider=NoPlanProvider()
        rt=await start_product_runtime(tmp_path,model_provider=provider)
        try:
            try:
                await rt.missions.run('Orquestre uma missão complexa ponta a ponta para executar e configurar o projeto.')
            except RuntimeError as exc:
                assert 'plano de execução verificável' in str(exc)
            else:
                raise AssertionError('A missão deveria exigir EXECUTION_PLAN.')
            assert provider.calls == 4
        finally: await rt.close()
    asyncio.run(run())
