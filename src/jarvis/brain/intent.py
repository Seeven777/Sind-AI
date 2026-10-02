from dataclasses import dataclass

@dataclass(slots=True,frozen=True)
class Intent:
    name:str
    confidence:float
    reason:str

class IntentRouter:
    TEAM_TERMS=(
        'missão completa','missao completa','monte uma equipe','equipe de agentes',
        'faça uma campanha','faca uma campanha','crie uma campanha','desenvolva um plano',
        'crie um projeto','trabalhem nisso','delegue'
    )
    RESEARCH_TERMS=('pesquise','pesquisa','investigue','investigar','levante','estude','research')
    DEVELOPER_TERMS=(
        'crie código','crie um código','escreva código','programe','implemente',
        'corrija o código','corrija este código','desenvolva software','desenvolva um script',
        'crie um script','refatore','debugue','debug'
    )
    MEMORY_TERMS=(
        'organize sua memória','organize sua memoria','revise sua memória','revise sua memoria',
        'curadoria de memória','curadoria de memoria','audite sua memória','audite sua memoria'
    )
    INBOX_TERMS=(
        'minha caixa de entrada','meu inbox','resuma meu inbox','resuma minha caixa',
        'o que chegou','triagem da caixa','trie minha caixa','verifique minha caixa'
    )
    BRIEFING_TERMS=(
        'me dê meu briefing','me de meu briefing','briefing do dia','briefing de hoje',
        'resumo do meu dia','o que merece atenção hoje','o que merece atencao hoje'
    )
    TIME_TERMS=('que horas são','que horas sao','hora atual','horário atual','horario atual')
    BROWSER_OPEN_TERMS=('abra o site ','abra a url ','abrir o site ','abrir a url ')
    WINDOWS_LIST_TERMS=('liste as janelas','listar janelas','quais janelas estão abertas','quais janelas estao abertas')
    WINDOWS_ACTIVATE_TERMS=('ative a janela ','ativar a janela ','abra a janela ')
    WHATSAPP_TERMS=('envie uma mensagem no whatsapp para ','mande uma mensagem no whatsapp para ','whatsapp para ')
    GENERIC_ACTION_TERMS=(
        'faça no computador ','faca no computador ','execute no computador ',
        'use o navegador ','acesse ','clique em ','digite em ','preencha ',
        'use a ferramenta ','execute a ferramenta '
    )

    def classify(self,text):
        lowered=text.lower().strip()
        if any(term in lowered for term in self.BRIEFING_TERMS):
            return Intent('briefing',.99,'briefing request')
        if any(term in lowered for term in self.INBOX_TERMS):
            return Intent('inbox',.98,'inbox triage request')
        if any(term in lowered for term in self.MEMORY_TERMS):
            return Intent('memory_curator',.98,'memory curation keyword')
        if any(term in lowered for term in self.DEVELOPER_TERMS):
            return Intent('developer',.96,'software development keyword')
        if any(term in lowered for term in self.TIME_TERMS):
            return Intent('operator_time',.99,'system time request')
        if any(lowered.startswith(term) for term in self.BROWSER_OPEN_TERMS):
            return Intent('operator_browser_open',.99,'browser open request')
        if any(term in lowered for term in self.WINDOWS_LIST_TERMS):
            return Intent('operator_windows_list',.99,'windows list request')
        if any(lowered.startswith(term) for term in self.WINDOWS_ACTIVATE_TERMS):
            return Intent('operator_windows_activate',.96,'windows activate request')
        if any(lowered.startswith(term) for term in self.WHATSAPP_TERMS):
            return Intent('operator_whatsapp_send',.99,'whatsapp send request')
        if any(lowered.startswith(term) for term in self.GENERIC_ACTION_TERMS):
            return Intent('tool_plan',.90,'generic executable action')
        if lowered.startswith(('liste a pasta ','listar pasta ','liste a pasta:','listar pasta:')):
            return Intent('operator_list',.99,'directory listing request')
        if lowered.startswith(('leia o arquivo ','ler arquivo ','leia o arquivo:','ler arquivo:')):
            return Intent('operator_read',.99,'file read request')
        if lowered.startswith(('crie arquivo ','crie o arquivo ','escreva arquivo ','escreva o arquivo ')):
            return Intent('operator_write',.98,'workspace write request')
        if any(term in lowered for term in self.TEAM_TERMS):
            return Intent('team_mission',.95,'team mission keyword')
        if any(term in lowered for term in self.RESEARCH_TERMS):
            return Intent('research',.92,'research keyword')
        return Intent('chat',.70,'default conversational route')
