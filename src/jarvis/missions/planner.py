from __future__ import annotations
from dataclasses import dataclass

@dataclass(slots=True, frozen=True)
class MissionPlan:
    agents: tuple[str, ...]
    reason: str
    mode: str = 'standard'
    research_external_allowed: bool = True
    creator_gate_required: bool = False
    operator_required: bool = False

class MissionPlanner:
    SOFTWARE=('código','codigo','python','javascript','typescript','software','bug','erro','api','backend','frontend','banco de dados','sql','site','aplicação','aplicacao','repositório','repositorio','implemente','programa','script')
    CREATIVE=('campanha','post','carrossel','reels','roteiro','conteúdo','conteudo','copy','legenda','marketing','instagram','design','publicação','publicacao')
    ANALYTIC=('analise','análise','dados','métricas','metricas','relatório','relatorio','compare','comparação','comparacao','diagnóstico','diagnostico','estratégia','estrategia')
    RESEARCH=('pesquise','pesquisa','investigue','mercado','lei','jurisprudência','jurisprudencia','fonte','notícia','noticia','tendência','tendencia','estudo')
    COMPLEX=('missão complexa','missao complexa','orquestre uma missão','orquestre uma missao','orquestre a missão','orquestre a missao','orquestração completa','orquestracao completa','pipeline completo','fluxo completo','processo completo','multiagente completo','multiagente','ponta a ponta','end-to-end','end to end')
    EXECUTION=('execute','executar','coloque em prática','coloque em pratica','aplique','aplicar','altere','alterar','crie o arquivo','escreva o arquivo','publique','envie','mande','abra','clique','preencha','instale','configure')
    def __init__(self,*,specialist_router=None,specialist_limit:int=1):
        self.specialist_router=specialist_router
        self.specialist_limit=max(0,int(specialist_limit))
    def _is_complex(self,text): return any(term in text for term in self.COMPLEX)
    def _complex_plan(self,objective):
        text=objective.lower()
        return MissionPlan(
            ('memory.curator','research.general','intelligence.analyst','creative.creator','engineering.developer','operations.operator','review.verifier'),
            'complex orchestration contract','complex',False,True,any(x in text for x in self.EXECUTION)
        )
    def build(self,objective):
        text=objective.lower()
        if self._is_complex(text): return self._complex_plan(objective)
        pipeline=[]
        software=any(x in text for x in self.SOFTWARE); creative=any(x in text for x in self.CREATIVE); analytic=any(x in text for x in self.ANALYTIC); research=any(x in text for x in self.RESEARCH)
        if research or creative or analytic or software: pipeline.append('research.general')
        if analytic or creative or software: pipeline.append('intelligence.analyst')
        routed=[]
        if self.specialist_router is not None and self.specialist_limit:
            try:routed=list(self.specialist_router.route(objective,limit=self.specialist_limit))
            except Exception:routed=[]
        for route in routed:
            aid=getattr(route,'agent_id',None)
            if aid:pipeline.append(aid)
        pipeline.append('engineering.developer' if software else 'creative.creator')
        pipeline.append('review.verifier')
        unique=[]
        for agent in pipeline:
            if agent not in unique:unique.append(agent)
        reason=[]
        if research:reason.append('research')
        if analytic:reason.append('analysis')
        if software:reason.append('engineering')
        if creative:reason.append('creative')
        if not reason:reason.append('general knowledge work')
        if routed:reason.append('agency specialists: '+', '.join(r.slug for r in routed))
        return MissionPlan(tuple(unique),', '.join(reason))
