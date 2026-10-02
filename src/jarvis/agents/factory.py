from __future__ import annotations

import json
from pathlib import Path

from .artifact_agent import ArtifactAgent
from .base import AgentCard


class ConfigurableArtifactAgent(ArtifactAgent):
    def __init__(self,*,card,system_prompt,artifact_name='custom-agent-output.md',**kwargs):
        self.card=card
        self.system_prompt=system_prompt
        self.artifact_name=artifact_name
        super().__init__(**kwargs)


class AgentFactory:
    """Persistent custom-agent definitions without modifying Jarvis core."""

    def __init__(self,*,path:Path,registry,llm_kwargs):
        self.path=Path(path)
        self.registry=registry
        self.llm_kwargs=llm_kwargs
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.load()

    def _read(self):
        if not self.path.exists():return []
        try:return json.loads(self.path.read_text(encoding='utf-8'))
        except Exception:return []

    def _write(self,items):
        self.path.write_text(
            json.dumps(items,ensure_ascii=False,indent=2),encoding='utf-8'
        )

    def load(self):
        for item in self._read():
            try:self._register(item)
            except Exception:continue

    def _register(self,item):
        card=AgentCard(
            item['agent_id'],item['name'],item.get('department','Custom'),
            item['mission'],tuple(item.get('capabilities') or ()),
            tuple(item.get('tools') or ()),item.get('model_capability','reasoning'),True
        )
        self.registry.register_card(card)
        runtime=ConfigurableArtifactAgent(
            card=card,
            system_prompt=item.get('system_prompt') or (
                f"Você é {card.name}. Sua missão: {card.mission}. "
                "Não invente execução de ferramentas. Escreva em português do Brasil."
            ),
            artifact_name=item.get('artifact_name') or f"{card.agent_id.replace('.','-')}.md",
            **self.llm_kwargs,
        )
        self.registry.register_runtime(card.agent_id,runtime)
        return card

    def create(
        self,*,agent_id,name,mission,department='Custom',
        capabilities=(),tools=(),model_capability='reasoning',
        system_prompt=None,artifact_name=None
    ):
        if agent_id in {c.agent_id for c in self.registry.cards()}:
            raise ValueError(f'Agent ID já existe: {agent_id}')
        item={
            'agent_id':agent_id,'name':name,'mission':mission,
            'department':department,'capabilities':list(capabilities),
            'tools':list(tools),'model_capability':model_capability,
            'system_prompt':system_prompt or (
                f"Você é {name}, agente especialista do Jarvis Next. "
                f"Sua missão é: {mission}. "
                "Trabalhe apenas com o contexto recebido. Não invente ações externas. "
                "Produza uma entrega verificável em português do Brasil."
            ),
            'artifact_name':artifact_name or f"{agent_id.replace('.','-')}.md",
        }
        items=self._read();items.append(item);self._write(items)
        card=self._register(item)
        return {
            'agent_id':card.agent_id,'name':card.name,
            'department':card.department,'capabilities':list(card.capabilities)
        }

    def definitions(self):
        return self._read()
