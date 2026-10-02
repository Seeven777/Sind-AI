from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

from jarvis.models import ChatMessage


_SKILL_SYSTEM="""Você é o Skill Builder do Jarvis Next.
Gere apenas uma skill Python pequena, determinística e testável.
A skill NÃO pode:
- alterar o core do Jarvis;
- baixar ou executar binários;
- acessar credenciais;
- usar shell;
- usar eval/exec;
- fazer rede sem uma permissão explícita;
- escrever fora do diretório de trabalho.

Responda SOMENTE com JSON válido:
{
  "executor_py": "código Python com def execute(payload): ...",
  "test_py": "teste pytest que importa execute e valida um caso real",
  "capabilities": ["..."],
  "permissions": []
}
"""


class SkillGenerationError(RuntimeError):
    pass


def _extract_json(text):
    value=text.strip()
    if value.startswith('```'):
        value=re.sub(r'^```(?:json)?\s*','',value)
        value=re.sub(r'\s*```$','',value)
    try:return json.loads(value)
    except json.JSONDecodeError:
        start=value.find('{');end=value.rfind('}')
        if start>=0 and end>start:
            return json.loads(value[start:end+1])
        raise


def _static_guard(code):
    forbidden=(
        'subprocess','os.system','eval(','exec(','socket','requests',
        'urllib.request','ctypes','win32','pywinauto','shutil.rmtree'
    )
    lower=code.lower()
    hits=[item for item in forbidden if item.lower() in lower]
    if hits:
        raise SkillGenerationError(
            'Código gerado contém primitivas bloqueadas: '+', '.join(hits)
        )


class SkillGenerationService:
    def __init__(self,*,skill_manager,model_registry,model_router):
        self.skill_manager=skill_manager
        self.model_registry=model_registry
        self.model_router=model_router

    async def generate(self,skill_id,description):
        scaffold=self.skill_manager.create_scaffold(
            skill_id,description,(skill_id,)
        )
        folder=Path(scaffold['path'])
        route=self.model_router.route(
            capability='coding',privacy='local',budget='free'
        )
        provider=self.model_registry.get(route.provider)
        response=await asyncio.to_thread(
            provider.chat,
            [ChatMessage('user',f"SKILL ID: {skill_id}\nOBJETIVO: {description}")],
            model=route.model,system=_SKILL_SYSTEM
        )
        try:
            payload=_extract_json(response.content)
        except Exception as exc:
            raise SkillGenerationError(
                f'O modelo não retornou JSON de skill válido: {exc}'
            ) from exc

        executor=str(payload.get('executor_py') or '')
        test=str(payload.get('test_py') or '')
        if 'def execute(' not in executor:
            raise SkillGenerationError('Skill gerada não define execute(payload).')
        if not test.strip():
            raise SkillGenerationError('Skill gerada não possui teste.')
        _static_guard(executor)
        _static_guard(test)

        (folder/'executor.py').write_text(executor,encoding='utf-8')
        (folder/'tests'/'test_executor.py').write_text(test,encoding='utf-8')

        capabilities=payload.get('capabilities') or [skill_id]
        permissions=payload.get('permissions') or []
        manifest=(
            '[skill]\n'
            f'id = {json.dumps(skill_id)}\n'
            'version = "0.1.0"\n'
            f'description = {json.dumps(description,ensure_ascii=False)}\n'
            'entrypoint = "executor.py"\n'
            f'permissions = {json.dumps(list(permissions),ensure_ascii=False)}\n'
            f'capabilities = {json.dumps(list(capabilities),ensure_ascii=False)}\n'
        )
        (folder/'manifest.toml').write_text(manifest,encoding='utf-8')
        test_result=self.skill_manager.test(folder)
        return {
            'skill_id':skill_id,
            'path':str(folder),
            'model':response.model,
            'provider':response.provider,
            'test':test_result,
            'ready_for_install':bool(test_result.get('passed')),
        }
