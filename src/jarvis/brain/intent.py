from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Intent:
    name: str
    confidence: float
    reason: str


class IntentRouter:
    TEAM_TERMS = (
        'missão completa','missao completa','monte uma equipe','equipe de agentes',
        'faça uma campanha','faca uma campanha','crie uma campanha','desenvolva um plano',
        'crie um projeto','trabalhem nisso','delegue'
    )
    RESEARCH_TERMS = ('pesquise','pesquisa','investigue','investigar','levante','estude','research')
    WEB_TERMS = (
        'pesquise na internet','pesquise na web','busque na internet','busque na web',
        'acesse a internet','acesso à internet','acesso a internet','últimas notícias','ultimas noticias',
        'notícias de hoje','noticias de hoje','previsão do tempo','previsao do tempo',
        'previsão do clima','previsao do clima','clima para hoje','clima de hoje','clima atual',
        'clima hoje','tempo hoje','tempo agora','meteorologia hoje','temperatura agora',
        'cotação atual','cotacao atual','preço atual','preco atual',
        'informações em tempo real','informacoes em tempo real','dados em tempo real'
    )
    DEVELOPER_TERMS = (
        'crie código','crie um código','escreva código','programe','implemente',
        'corrija o código','corrija este código','desenvolva software','desenvolva um script',
        'crie um script','refatore','debugue','debug'
    )
    MEMORY_TERMS = (
        'organize sua memória','organize sua memoria','revise sua memória','revise sua memoria',
        'curadoria de memória','curadoria de memoria','audite sua memória','audite sua memoria'
    )
    INBOX_TERMS = (
        'minha caixa de entrada','meu inbox','resuma meu inbox','resuma minha caixa',
        'o que chegou','triagem da caixa','trie minha caixa','verifique minha caixa',
        'meus e-mails','meus emails','e-mails recentes','emails recentes','meus e-mails recentes',
        'meus emails recentes','verifique meus e-mails','verifique meus emails'
    )
    CALENDAR_TERMS = (
        'meu calendário','meu calendario','meus compromissos','compromissos de hoje',
        'agenda de hoje','minha agenda','eventos de hoje','reuniões de hoje','reunioes de hoje'
    )
    BRIEFING_TERMS = (
        'me dê meu briefing','me de meu briefing','briefing do dia','briefing de hoje',
        'briefing completo','briefing completo do dia','briefing completo de hoje','meu briefing completo',
        'faça meu briefing','faca meu briefing','refaça meu briefing','refaca meu briefing','inicie meu briefing','iniciar meu briefing',
        'resumo do meu dia','o que merece atenção hoje','o que merece atencao hoje',
        'o que merece minha atenção hoje','o que merece minha atencao hoje',
        'prioridades de hoje','minhas prioridades hoje'
    )
    TIME_TERMS = ('que horas são','que horas sao','hora atual','horário atual','horario atual')
    BROWSER_OPEN_TERMS = ('abra o site ','abra a url ','abrir o site ','abrir a url ')
    WINDOWS_LIST_TERMS = ('liste as janelas','listar janelas','quais janelas estão abertas','quais janelas estao abertas')
    WINDOWS_ACTIVATE_TERMS = ('ative a janela ','ativar a janela ','abra a janela ')
    WHATSAPP_TERMS = ('envie uma mensagem no whatsapp para ','mande uma mensagem no whatsapp para ','whatsapp para ')
    GENERIC_ACTION_TERMS = (
        'faça no computador ','faca no computador ','execute no computador ',
        'use o navegador ','acesse ','clique em ','digite em ','preencha ',
        'use a ferramenta ','execute a ferramenta '
    )


    @staticmethod
    def _looks_like_morning_sequence(lowered):
        # Natural commands that mean "run the interactive morning ritual", not
        # "write me a prose summary". Keep this deterministic so the UI never
        # depends on an LLM guessing whether it should materialize the briefing.
        if 'briefing' not in lowered:
            return False
        action_words = (
            'faça','faca','refaça','refaca','inicie','iniciar','execute','executar','rode','rodar',
            'mostre','mostrar','abra','abrir','completo','completa','manhã','manha'
        )
        return any(x in lowered for x in action_words)

    @staticmethod
    def _looks_like_live_weather(lowered):
        weather_words = ('clima','tempo','temperatura','chuva','meteorologia','previsão','previsao')
        live_words = ('hoje','amanhã','amanha','agora','atual','previsão','previsao','gadget')
        return any(x in lowered for x in weather_words) and any(x in lowered for x in live_words)

    @staticmethod
    def _looks_like_live_news(lowered):
        news_words = ('notícia','noticia','notícias','noticias','manchete','manchetes','news')
        live_words = ('última','ultima','últimas','ultimas','hoje','agora','recentes','gadget')
        return any(x in lowered for x in news_words) and any(x in lowered for x in live_words)

    def classify(self, text):
        lowered = text.lower().strip()
        has_inbox = any(term in lowered for term in self.INBOX_TERMS)
        has_calendar = any(term in lowered for term in self.CALENDAR_TERMS)
        has_briefing = any(term in lowered for term in self.BRIEFING_TERMS)

        if self._looks_like_morning_sequence(lowered):
            return Intent('morning_sequence', .999, 'interactive morning briefing request')

        # Requests that combine personal sources should always use the live
        # briefing path so Jarvis synchronizes connectors before answering.
        if has_briefing or (has_inbox and has_calendar):
            return Intent('briefing', .99, 'live personal briefing request')
        if has_calendar:
            return Intent('briefing', .98, 'calendar briefing request')
        if has_inbox:
            return Intent('inbox', .98, 'inbox triage request')
        if any(term in lowered for term in self.MEMORY_TERMS):
            return Intent('memory_curator', .98, 'memory curation keyword')
        if any(term in lowered for term in self.DEVELOPER_TERMS):
            return Intent('developer', .96, 'software development keyword')
        if any(term in lowered for term in self.TIME_TERMS):
            return Intent('operator_time', .99, 'system time request')
        if any(lowered.startswith(term) for term in self.BROWSER_OPEN_TERMS):
            return Intent('operator_browser_open', .99, 'browser open request')
        if any(term in lowered for term in self.WINDOWS_LIST_TERMS):
            return Intent('operator_windows_list', .99, 'windows list request')
        if any(lowered.startswith(term) for term in self.WINDOWS_ACTIVATE_TERMS):
            return Intent('operator_windows_activate', .96, 'windows activate request')
        if any(lowered.startswith(term) for term in self.WHATSAPP_TERMS):
            return Intent('operator_whatsapp_send', .99, 'whatsapp send request')
        if any(lowered.startswith(term) for term in self.GENERIC_ACTION_TERMS):
            return Intent('tool_plan', .90, 'generic executable action')
        if lowered.startswith(('liste a pasta ','listar pasta ','liste a pasta:','listar pasta:')):
            return Intent('operator_list', .99, 'directory listing request')
        if lowered.startswith(('leia o arquivo ','ler arquivo ','leia o arquivo:','ler arquivo:')):
            return Intent('operator_read', .99, 'file read request')
        if lowered.startswith(('crie arquivo ','crie o arquivo ','escreva arquivo ','escreva o arquivo ')):
            return Intent('operator_write', .98, 'workspace write request')
        # Live information is a first-class read capability. This semantic guard
        # catches natural variants such as "previsão do clima para hoje" and
        # "abra o gadget do clima" instead of letting a generic chat model
        # incorrectly claim that Jarvis has no internet or cannot materialize UI.
        if self._looks_like_live_weather(lowered):
            return Intent('research', .995, 'live weather request')
        if self._looks_like_live_news(lowered):
            return Intent('research', .995, 'live news request')
        if any(term in lowered for term in self.TEAM_TERMS):
            return Intent('team_mission', .95, 'team mission keyword')
        if any(term in lowered for term in self.WEB_TERMS):
            return Intent('research', .98, 'live web information keyword')
        if any(term in lowered for term in self.RESEARCH_TERMS):
            return Intent('research', .92, 'research keyword')
        return Intent('chat', .70, 'default conversational route')
