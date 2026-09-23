from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class AgentRole:
    id: str
    name: str
    purpose: str
    prompt: str
    triggers: tuple[str, ...]
    mode: str = "fast"


class AgentRegistry:
    """Catálogo leve de especialistas. Papéis não significam processos/modelos simultâneos."""

    def __init__(self):
        self.roles: Dict[str, AgentRole] = {
            "planner": AgentRole(
                "planner", "Planner",
                "Quebra objetivos complexos em etapas verificáveis e identifica dependências.",
                """Você é o Planner do Jarvis. Transforme o objetivo em um plano curto e executável.
Identifique: resultado esperado, etapas, dependências, acessos/ferramentas necessários, riscos e critério de conclusão.
Não execute nada e não escreva chain-of-thought. Produza apenas um plano operacional conciso em português.""",
                ("planeje", "planejar", "projeto", "estratégia", "estrategia", "complex", "automat", "implemente"),
                "fast",
            ),
            "researcher": AgentRole(
                "researcher", "Researcher",
                "Pesquisa e organiza evidências externas e lacunas factuais.",
                """Você é o Researcher do Jarvis. Analise o objetivo e indique quais fatos precisam ser pesquisados,
quais fontes primárias/oficiais priorizar, quais evidências seriam suficientes e quais incertezas devem ser preservadas.
Não invente dados e não execute ferramentas. Entregue uma orientação curta para o executor.""",
                ("pesquis", "fonte", "notícia", "noticia", "lei", "portaria", "norma", "mercado", "tendência", "tendencia"),
                "fast",
            ),
            "institutional": AgentRole(
                "institutional", "Institutional",
                "Aplica contexto SindPetshop-SP, CCTs, treinamento e conhecimento institucional.",
                """Você é o especialista institucional do Jarvis para o SindPetshop-SP. Aponte quais conhecimentos internos,
CCTs, documentos, procedimentos, serviços ou restrições institucionais precisam ser consultados para cumprir o objetivo.
Não invente cláusulas nem políticas. Entregue orientação concisa ao executor.""",
                ("sindpet", "cct", "convenção", "convencao", "sindicato", "trabalhador", "institucional", "equipe", "treinamento"),
                "fast",
            ),
            "operator": AgentRole(
                "operator", "Operator",
                "Desenha sequências seguras de ações no desktop, navegador, arquivos e aplicativos.",
                """Você é o Operator do Jarvis. Proponha a sequência mais direta de ações para executar a tarefa usando
browser, desktop, arquivos e aplicativos. Separe ações reversíveis das sensíveis e indique onde é necessária confirmação.
Não execute nada e não invente sucesso.""",
                ("abra", "envie", "mande", "clique", "navegue", "whatsapp", "browser", "arquivo", "desktop", "aplicativo"),
                "fast",
            ),
            "analyst": AgentRole(
                "analyst", "Analyst",
                "Interpreta métricas, dashboards, dados e define análises úteis.",
                """Você é o Analyst do Jarvis. Para o objetivo dado, defina as métricas/dados relevantes, comparações,
segmentações e testes que realmente ajudam a decisão. Identifique dados ausentes. Não invente números.""",
                ("dashboard", "métrica", "metrica", "analytics", "insight", "dados", "desempenho", "resultado", "compar"),
                "fast",
            ),
            "content": AgentRole(
                "content", "Content",
                "Transforma pesquisa/contexto em comunicação, campanhas e conteúdo.",
                """Você é o Content Specialist do Jarvis. Analise objetivo, público, formato, tom, retenção e CTA.
Indique uma estrutura de conteúdo adequada e riscos de comunicação. Não crie fatos; use apenas evidências fornecidas.""",
                ("publicação", "publicacao", "post", "reels", "carrossel", "campanha", "legenda", "conteúdo", "conteudo", "roteiro"),
                "fast",
            ),
            "developer": AgentRole(
                "developer", "Developer",
                "Planeja código, site, automações e integrações técnicas.",
                """Você é o Developer do Jarvis. Defina abordagem técnica, componentes afetados, validações, rollback e testes.
Prefira mudanças pequenas e verificáveis. Não afirme que código funciona sem teste.""",
                ("código", "codigo", "site", "wordpress", "css", "javascript", "python", "api", "integra", "deploy", "git", "vercel"),
                "fast",
            ),
            "reviewer": AgentRole(
                "reviewer", "Reviewer",
                "Audita a entrega e devolve uma versão final melhor quando necessário.",
                """Você é o Reviewer do Jarvis. Receba objetivo, evidências/ações e uma resposta candidata.
Verifique: cumprimento do pedido, contradições, afirmações sem base, etapas faltando, riscos e clareza.
Retorne SOMENTE a resposta final revisada para o usuário em português. Não exponha sua análise interna.""",
                tuple(),
                "fast",
            ),
        }

    def get(self, role_id: str):
        return self.roles.get(str(role_id or "").strip().lower())

    def list(self) -> List[dict]:
        return [
            {"id": r.id, "name": r.name, "purpose": r.purpose, "mode": r.mode}
            for r in self.roles.values()
        ]

    def select(self, text: str, max_roles: int = 2) -> List[AgentRole]:
        q = str(text or "").lower()
        scored = []
        strong_cues = {
            "researcher": ("pesquis", "fontes", "fonte oficial", "investigue"),
            "institutional": ("sindpet", "cct", "convenção", "convencao", "sindicato"),
            "operator": ("abra", "envie", "mande", "clique", "whatsapp"),
            "analyst": ("dashboard", "métricas", "metricas", "dados", "desempenho"),
            "content": ("publicação", "publicacao", "reels", "carrossel", "campanha", "roteiro"),
            "developer": ("código", "codigo", "api", "site", "deploy", "integração", "integracao"),
        }
        priority = {"researcher": 0, "institutional": 1, "analyst": 2, "content": 3, "developer": 4, "operator": 5}
        for role in self.roles.values():
            if role.id in {"planner", "reviewer"}:
                continue
            score = sum(2 for trigger in role.triggers if trigger in q)
            if any(cue in q for cue in strong_cues.get(role.id, ())):
                score += 3
            if score:
                scored.append((score, priority.get(role.id, 99), role))
        scored.sort(key=lambda x: (-x[0], x[1], x[2].id))
        return [role for _, _, role in scored[:max(0, int(max_roles))]]

    def ids(self) -> Iterable[str]:
        return self.roles.keys()
