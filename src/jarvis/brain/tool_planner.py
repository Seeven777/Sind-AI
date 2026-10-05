from __future__ import annotations

import asyncio
import json
import re

from jarvis.models import ChatMessage


_TOOL_SPECS={
    'system.time':{
        'description':'Obter data/hora UTC real do computador.',
        'payload':{},
    },
    'files.read_text':{
        'description':'Ler arquivo de texto existente.',
        'payload':{'path':'caminho absoluto'},
    },
    'files.list_directory':{
        'description':'Listar arquivos e pastas.',
        'payload':{'path':'caminho absoluto','limit':100},
    },
    'files.write_workspace_text':{
        'description':'Criar/alterar arquivo somente no workspace seguro do Jarvis. Exige aprovação.',
        'payload':{'relative_path':'arquivo.txt','content':'texto'},
    },
    'files.write_workspace_pdf':{
        'description':'Criar PDF somente no workspace seguro do Jarvis, validar que o PDF abre e contém páginas. Exige aprovação.',
        'payload':{'relative_path':'relatorio.pdf','title':'Título','content':'conteúdo do documento'},
    },
    'web.search':{
        'description':'Pesquisar informação pública na web.',
        'payload':{'query':'consulta','limit':5},
    },
    'web.fetch':{
        'description':'Ler conteúdo público de uma URL http/https.',
        'payload':{'url':'https://...'},
    },
    'browser.open':{
        'description':'Abrir uma URL no navegador controlado pelo Jarvis.',
        'payload':{'url':'https://...'},
    },
    'browser.snapshot':{
        'description':'Observar página atualmente aberta no navegador controlado.',
        'payload':{'max_chars':12000},
    },
    'browser.fill':{
        'description':'Preencher um campo no browser por seletor CSS. Exige aprovação.',
        'payload':{'selector':'css selector','text':'texto'},
    },
    'browser.click':{
        'description':'Clicar em elemento no browser por seletor CSS. Exige aprovação.',
        'payload':{'selector':'css selector'},
    },
    'windows.list':{
        'description':'Listar janelas abertas no Windows.',
        'payload':{},
    },
    'windows.inspect':{
        'description':'Inspecionar controles UIA de uma janela.',
        'payload':{'window_title_re':'regex do título','depth':2},
    },
    'windows.activate':{
        'description':'Colocar uma janela em foco. Exige aprovação.',
        'payload':{'window_title_re':'regex do título'},
    },
    'windows.set_text':{
        'description':'Preencher controle UIA de uma janela. Exige aprovação.',
        'payload':{
            'window_title_re':'regex','title':'texto opcional',
            'auto_id':'id opcional','control_type':'Edit','text':'texto'
        },
    },
    'windows.click':{
        'description':'Clicar controle UIA. Exige aprovação e posterior verificação da meta.',
        'payload':{
            'window_title_re':'regex','title':'texto opcional',
            'auto_id':'id opcional','control_type':'Button'
        },
    },
    'whatsapp.send_message':{
        'description':'Enviar mensagem real pelo WhatsApp Desktop e verificar a mensagem na interface. Exige aprovação.',
        'payload':{'contact':'nome do contato','message':'mensagem'},
    },
}

_SYSTEM="""Você é o planejador de ferramentas do Jarvis.
Escolha no máximo UMA ferramenta para cumprir a ação do usuário.
Nunca invente ferramenta. Nunca omita dados obrigatórios.
Se nenhuma ferramenta puder cumprir a solicitação, retorne tool_id null.
Responda SOMENTE JSON válido:
{"tool_id":"id ou null","payload":{},"reason":"curto"}
"""


class ToolPlanError(RuntimeError):pass


def _extract_json(text):
    value=text.strip()
    if value.startswith('```'):
        value=re.sub(r'^```(?:json)?\s*','',value)
        value=re.sub(r'\s*```$','',value)
    start=value.find('{');end=value.rfind('}')
    if start>=0 and end>=start:value=value[start:end+1]
    return json.loads(value)


class ToolPlanner:
    def __init__(self,*,model_registry,model_router,tool_registry):
        self.model_registry=model_registry
        self.model_router=model_router
        self.tool_registry=tool_registry

    def specs(self):
        allowed=set(self.tool_registry.list_ids())
        return {k:v for k,v in _TOOL_SPECS.items() if k in allowed}

    async def plan(self,request):
        specs=self.specs()
        route=self.model_router.route(capability='tool_use',privacy='local',budget='free')
        provider=self.model_registry.get(route.provider)
        prompt=(
            f"SOLICITAÇÃO:\n{request}\n\n"
            f"FERRAMENTAS DISPONÍVEIS:\n{json.dumps(specs,ensure_ascii=False,indent=2)}"
        )
        response=await asyncio.to_thread(
            provider.chat,[ChatMessage('user',prompt)],
            model=route.model,system=_SYSTEM
        )
        try:raw=_extract_json(response.content)
        except Exception as exc:raise ToolPlanError(f'Plano de ferramenta inválido: {exc}') from exc
        tool_id=raw.get('tool_id')
        if tool_id in (None,'null',''):
            return {'tool_id':None,'payload':{},'reason':raw.get('reason','sem ferramenta adequada')}
        if tool_id not in specs:
            raise ToolPlanError(f'Ferramenta não permitida no plano: {tool_id}')
        payload=raw.get('payload')
        if not isinstance(payload,dict):
            raise ToolPlanError('payload precisa ser objeto JSON.')
        return {'tool_id':tool_id,'payload':payload,'reason':str(raw.get('reason') or '')}
