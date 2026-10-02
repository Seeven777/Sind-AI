from .base import AgentCard

def builtin_agent_cards():
    return (
        AgentCard(
            'research.general','Research','Research',
            'Investigar problemas, decompor perguntas e organizar evidências.',
            ('research','source_planning','synthesis'),(), 'reasoning', True,
        ),
        AgentCard(
            'intelligence.analyst','Analyst','Intelligence',
            'Cruzar artifacts e transformar pesquisa em análise e decisão.',
            ('analysis','reasoning','prioritization'),(), 'reasoning', True,
        ),
        AgentCard(
            'creative.creator','Creator','Creative',
            'Transformar análise em uma entrega clara, utilizável e alinhada ao objetivo.',
            ('writing','content','planning'),(), 'creative', True,
        ),
        AgentCard(
            'engineering.developer','Developer','Engineering',
            'Projetar implementações, código e testes sem alterar o core silenciosamente.',
            ('coding','architecture','testing','debugging'),(), 'coding', True,
        ),
        AgentCard(
            'operations.operator','Operator','Operations',
            'Executar ações reais com ferramentas autorizadas e evidência verificável.',
            ('execution','tool_use','verification'),
            (
                'system.time','files.read_text','files.list_directory',
                'files.write_workspace_text','web.search','web.fetch',
                'browser.open','browser.snapshot','browser.fill','browser.click',
                'windows.list','windows.inspect','windows.activate',
                'windows.set_text','windows.click','whatsapp.send_message'
            ),
            'tool_use', True,
        ),
        AgentCard(
            'review.verifier','Reviewer','Review',
            'Revisar a entrega, apontar falhas e verificar se ela atende à missão.',
            ('verification','quality','fact_check'),(), 'reasoning', True,
        ),
        AgentCard(
            'administration.inbox','Inbox','Administration',
            'Classificar e priorizar itens recebidos por connectors autorizados.',
            ('triage','prioritization','inbox'),(), 'fast', True,
        ),
        AgentCard(
            'memory.curator','Memory Curator','Memory',
            'Inspecionar, consolidar e sinalizar duplicidades na memória persistente.',
            ('memory','deduplication','quality'),(), 'fast', True,
        ),
    )
