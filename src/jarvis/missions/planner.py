from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True,frozen=True)
class MissionPlan:
    agents:tuple[str,...]
    reason:str


class MissionPlanner:
    """Deterministic team builder with optional specialist routing.

    The core pipeline remains stable. When an external specialist router is
    available, one or more read-only knowledge specialists can be inserted
    before the built-in delivery agent. This keeps real execution isolated in
    Operator and preserves the final independent Reviewer gate.
    """

    SOFTWARE=(
        'código','codigo','python','javascript','typescript','software','bug','erro',
        'api','backend','frontend','banco de dados','sql','site','aplicação','aplicacao',
        'repositório','repositorio','implemente','programa','script'
    )
    CREATIVE=(
        'campanha','post','carrossel','reels','roteiro','conteúdo','conteudo',
        'copy','legenda','marketing','instagram','design','publicação','publicacao'
    )
    ANALYTIC=(
        'analise','análise','dados','métricas','metricas','relatório','relatorio',
        'compare','comparação','comparacao','diagnóstico','diagnostico','estratégia','estrategia'
    )
    RESEARCH=(
        'pesquise','pesquisa','investigue','mercado','lei','jurisprudência','jurisprudencia',
        'fonte','notícia','noticia','tendência','tendencia','estudo'
    )

    def __init__(self,*,specialist_router=None,specialist_limit:int=1):
        self.specialist_router=specialist_router
        self.specialist_limit=max(0,int(specialist_limit))

    def build(self,objective):
        text=objective.lower()
        pipeline=[]

        software=any(x in text for x in self.SOFTWARE)
        creative=any(x in text for x in self.CREATIVE)
        analytic=any(x in text for x in self.ANALYTIC)
        research=any(x in text for x in self.RESEARCH)

        if research or creative or analytic or software:
            pipeline.append('research.general')
        if analytic or creative or software:
            pipeline.append('intelligence.analyst')

        routed=[]
        if self.specialist_router is not None and self.specialist_limit:
            try:
                routed=list(self.specialist_router.route(objective,limit=self.specialist_limit))
            except Exception:
                routed=[]
        for route in routed:
            agent_id=getattr(route,'agent_id',None)
            if agent_id:
                pipeline.append(agent_id)

        if software:
            pipeline.append('engineering.developer')
        elif creative:
            pipeline.append('creative.creator')
        else:
            # General knowledge-work delivery.
            pipeline.append('creative.creator')

        pipeline.append('review.verifier')

        # Preserve order and remove accidental duplicates.
        unique=[]
        for agent in pipeline:
            if agent not in unique:
                unique.append(agent)

        reason=[]
        if research:reason.append('research')
        if analytic:reason.append('analysis')
        if software:reason.append('engineering')
        if creative:reason.append('creative')
        if not reason:reason.append('general knowledge work')
        if routed:
            reason.append('agency specialists: '+', '.join(r.slug for r in routed))
        return MissionPlan(tuple(unique),', '.join(reason))
