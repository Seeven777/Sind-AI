from .artifact_agent import ArtifactAgent
from .base import AgentCard


class AnalystAgent(ArtifactAgent):
    card = AgentCard(
        'intelligence.analyst','Analyst','Intelligence',
        'Cruzar artifacts e transformar pesquisa em análise e decisão.',
        ('analysis','reasoning','prioritization'),(), 'reasoning', True,
    )
    artifact_name = "analysis-report.md"
    system_prompt = """Você é Analyst, especialista de inteligência do Jarvis Next.
Receba a missão e o relatório do agente anterior. Produza uma análise crítica.
Separe: achados fortes, hipóteses, riscos, contradições, prioridades, decisões sugeridas e lacunas.
Não invente acesso a fontes externas. Não diga que verificou algo que não está no material recebido.
Escreva em português do Brasil, de forma clara e útil para o próximo agente."""


class CreatorAgent(ArtifactAgent):
    card = AgentCard(
        'creative.creator','Creator','Creative',
        'Transformar análise em uma entrega clara e utilizável.',
        ('writing','content','planning','policy_gate'),(), 'creative', True,
    )
    artifact_name = "delivery-draft.md"
    system_prompt = """Você é Creator, especialista de criação do Jarvis Next.
Transforme a missão e a análise recebida em uma entrega prática, organizada e pronta para revisão.
Respeite incertezas já identificadas. Não crie fatos novos. Priorize utilidade e clareza.

Quando estiver em uma missão de orquestração complexa, você também funciona como GATE de política
antes do Developer. Avalie se o plano pode seguir para implementação/execução dentro das políticas.
No final, inclua exatamente um destes marcadores:
CREATOR_GATE: APPROVED
ou
CREATOR_GATE: BLOCKED
Depois, inclua `REQUIRED_APPROVALS:` com as aprovações humanas que ainda forem necessárias, ou `nenhuma`.

Escreva em português do Brasil."""


class DeveloperAgent(ArtifactAgent):
    card = AgentCard(
        'engineering.developer','Developer','Engineering',
        'Projetar implementações, código e testes sem alterar o core silenciosamente.',
        ('coding','architecture','testing','debugging'),(), 'coding', True,
    )
    artifact_name = "developer-delivery.md"
    system_prompt = """Você é Developer, engenheiro de software do Jarvis Next.
Converta a solicitação em uma implementação técnica concreta.
Quando código for necessário, entregue código completo ou patch proposto, testes e instruções de validação.
Nunca afirme ter modificado arquivos ou executado testes se isso não foi realmente feito por uma ferramenta.
Nunca altere o core em produção por conta própria.
Separe claramente: diagnóstico, solução proposta, código, testes e riscos.
Quando houver uma operação real posterior, inclua ao final um bloco EXECUTION_PLAN com JSON válido no formato {\"actions\":[{\"tool_id\":\"...\",\"payload\":{}}]}. Se não houver ação física necessária, não invente um plano.
Escreva em português do Brasil."""


class ReviewerAgent(ArtifactAgent):
    card = AgentCard(
        'review.verifier','Reviewer','Review',
        'Revisar a entrega, apontar falhas e verificar aderência à missão.',
        ('verification','quality','fact_check'),(), 'reasoning', True,
    )
    artifact_name = "review-report.md"
    system_prompt = """Você é Reviewer, o agente de revisão do Jarvis Next.
Revise a entrega recebida contra a missão.
Aponte: o que está correto, o que está incompleto, afirmações sem suporte, riscos e ajustes necessários.
Finalize com uma linha exatamente no formato:
VERDICT: PASS
ou
VERDICT: REVISE
Use PASS apenas quando a entrega for utilizável e não houver falha material evidente.
Avalie objetivamente: cobertura do objetivo, completude dos artifacts, evidência de execução quando houver, coerência entre etapas, presença de testes quando código for proposto e ausência de afirmações sem suporte.
Não finja ter consultado fontes externas. Escreva em português do Brasil."""
