class SelfAwareness:
    """Grounded self-knowledge from the actual runtime, not model imagination."""

    def __init__(self, services, actions, workflows, capabilities, models, hardware, knowledge, connectors=None, swarm=None, apprenticeship=None, demonstration=None, acquisition=None, long_horizon=None, workplace=None, experience=None):
        self.services = services
        self.actions = actions
        self.workflows = workflows
        self.capabilities = capabilities
        self.models = models
        self.hardware = hardware
        self.knowledge = knowledge
        self.connectors = connectors
        self.swarm = swarm
        self.apprenticeship = apprenticeship
        self.demonstration = demonstration
        self.acquisition = acquisition
        self.long_horizon = long_horizon
        self.workplace = workplace
        self.experience = experience

    def matches(self, text):
        t = str(text or "").lower().strip()
        patterns = (
            "o que você consegue", "o que voce consegue", "o que você sabe fazer", "o que voce sabe fazer",
            "quais ferramentas", "quais sistemas", "quais serviços", "quais servicos",
            "você consegue acessar", "voce consegue acessar", "você tem acesso", "voce tem acesso",
            "quais recursos", "suas capacidades", "suas ferramentas", "quais agentes", "seus agentes",
            "como eu te ensino", "como te ensinar", "você consegue aprender", "voce consegue aprender",
            "como você aprende sozinho", "como voce aprende sozinho", "adquirir novas capacidades", "lacunas de capacidade",
            "tarefas de longo prazo", "jobs persistentes", "trabalhar por horas", "continuar depois de reiniciar",
            "playbooks", "rotinas de trabalho", "workplace intelligence", "biblioteca de rotinas",
            "o que você aprendeu", "o que voce aprendeu", "mapa de competências", "mapa de competencias",
            "adaptações", "adaptacoes", "experiência acumulada", "experiencia acumulada",
        )
        return any(x in t for x in patterns)

    def snapshot(self):
        connectors = {}
        try:
            connectors = self.connectors.stats() if self.connectors else {}
        except Exception:
            connectors = {}
        return {
            "ok": True,
            "models": self.models.status(),
            "hardware": self.hardware.profile(),
            "services": self.services.list(daily=True),
            "actions": self.actions.stats(),
            "workflows": self.workflows.stats(),
            "capabilities": self.capabilities.stats(),
            "knowledge": self.knowledge.stats(),
            "connectors": connectors,
            "swarm": self.swarm.stats() if self.swarm else {},
            "apprenticeship": self.apprenticeship.stats() if self.apprenticeship else {},
            "demonstration": self.demonstration.status() if self.demonstration else {},
            "acquisition": self.acquisition.stats() if self.acquisition else {},
            "long_horizon": self.long_horizon.stats() if self.long_horizon else {},
            "workplace": self.workplace.stats() if self.workplace else {},
            "experience": self.experience.stats() if self.experience else {},
        }

    def _service_lines(self):
        rows = []
        for s in self.services.list(daily=True).get("items", []):
            use = s.get("when_to_use") or s.get("notes", "")
            access = s.get("access", "")
            rows.append(f"- **{s.get('name')}** — {use} Acesso: `{access}`.")
        return rows

    def _explicit_service(self, text):
        t = str(text or "").lower()
        common = {"sindpetshop", "sindpetshop-sp", "sind petshop", "sindicato", "site"}
        matches = []
        for item in self.services.items:
            aliases = [item.get("id", ""), item.get("name", "")] + list(item.get("aliases", []))
            for alias in aliases:
                a = str(alias or "").strip().lower()
                if not a or a in common:
                    continue
                if a in t:
                    matches.append((len(a), item))
                    break
        if not matches:
            return None
        matches.sort(key=lambda x: -x[0])
        return matches[0][1]

    def answer(self, text):
        t = str(text or "").lower()

        if any(k in t for k in ("o que você aprendeu", "o que voce aprendeu", "mapa de competências", "mapa de competencias", "adaptações", "adaptacoes", "experiência acumulada", "experiencia acumulada")):
            stats = self.experience.stats() if self.experience else {}
            retro = self.experience.retrospective() if self.experience else {}
            return (
                "Meu **Adaptive Experience** aprende sem alterar pesos do modelo: observo resultados reais, "
                "correções explícitas e o desempenho dos playbooks.\n\n"
                f"Estado atual: **{stats.get('events',0)} eventos de experiência**, "
                f"**{stats.get('competences',0)} competências perfiladas**, "
                f"**{stats.get('active_rules',0)} regras aprendidas** e "
                f"**{stats.get('candidates',{}).get('proposed',0)} adaptações pendentes**.\n"
                f"Taxa de sucesso na janela recente: **{retro.get('success_rate',0)}%**.\n\n"
                "Correções textuais seguras podem virar regras imediatamente; mudanças estruturais ficam como "
                "candidatos supervisionados. Jobs concluídos também podem virar novas rotinas persistentes."
            )

        if any(k in t for k in ("playbooks", "rotinas de trabalho", "workplace intelligence", "biblioteca de rotinas")):
            stats = self.workplace.stats() if self.workplace else {}
            return (
                f"Meu **Workplace Intelligence** possui **{stats.get('playbooks',0)} playbooks** em "
                f"**{stats.get('categories',0)} áreas de trabalho**. Eles cobrem conteúdo, analytics, redes, site, "
                "pesquisa, CCT, campanhas, equipe, operações, documentos, automação e qualidade.\n\n"
                "Eu uso esses playbooks como orientação antes de improvisar rotinas recorrentes e posso iniciá-los "
                "como Jobs persistentes com checkpoints."
            )

        if any(k in t for k in ("tarefas de longo prazo", "jobs persistentes", "trabalhar por horas", "continuar depois de reiniciar")):
            stats = self.long_horizon.stats() if self.long_horizon else {}
            return (
                "Consigo manter **jobs persistentes de longo prazo** em checkpoints. "
                "Etapas seguras podem ser retomadas depois de reiniciar o Jarvis; etapas com possível efeito externo "
                "pedem revisão antes de serem repetidas.\n\n"
                f"Estado atual: **{stats.get('jobs',0)} job(s)** registrados e **{stats.get('active',0)} ativo(s)**."
            )

        if "agentes" in t or "seus agentes" in t:
            roles = self.swarm.registry.list() if self.swarm else []
            if roles:
                lines = [f"- **{x['name']}** — {x['purpose']}" for x in roles]
                return "Meu Swarm local possui estes papéis especialistas:\n\n" + "\n".join(lines) + "\n\nEu escolho os especialistas automaticamente; você continua conversando apenas com o Jarvis."

        if any(x in t for x in ("como eu te ensino", "como te ensinar", "consegue aprender", "consigo te ensinar", "como você aprende sozinho", "como voce aprende sozinho", "adquirir novas capacidades")):
            return (
                "Posso adquirir competências de três formas persistentes:\n\n"
                "1. **Descoberta autônoma:** diga `Descubra como fazer ...`. Primeiro verifico Skills, Actions, Workflows e APIs existentes; depois tento compor uma Skill declarativa ou encontrar uma API pública segura.\n"
                "2. **Por explicação:** diga `Quero te ensinar como ...`, explique os passos e finalize com `finalizar ensino`.\n"
                "3. **Por demonstração:** diga `Observe enquanto eu faço ...`, execute a rotina no computador e finalize com `terminei a demonstração`. A demonstração vira uma Skill reutilizável; texto digitado é mascarado por privacidade.\n"
                "4. **Por experiência:** diga quando algo funcionou, falhou ou deve mudar. O Adaptive Experience atualiza confiança, cria regras e propõe adaptações para a próxima execução.\n"
                "5. **Por execução real:** um Job concluído pode ser transformado em uma nova rotina persistente.\n\n"
                "Aquisições automáticas não executam código arbitrário gerado pelo modelo. Mudanças estruturais continuam supervisionadas."
            )

        service = self._explicit_service(text)
        if service and any(k in t for k in ("acessar", "acesso", "ferramenta", "serviço", "servico", "sistema", "consegue", "pode")):
            caps = ", ".join(service.get("capabilities", []))
            return (
                f"Conheço **{service.get('name')}**. {service.get('when_to_use') or service.get('notes', '')}\n\n"
                f"**Como acesso:** `{service.get('access', 'não especificado')}`.  \n"
                f"**Capacidades registradas:** {caps or 'nenhuma capacidade específica registrada'}.\n\n"
                "Se a operação exigir login, uso apenas uma sessão já autenticada ou um conector autorizado; não invento credenciais."
            )

        if any(k in t for k in ("sindpetshop", "sindpetshop-sp", "sindicato", "ferramentas", "serviços", "servicos")):
            return (
                "Estas são as ferramentas/serviços cotidianos do SindPetshop-SP que estão mapeados no meu runtime e quando eu os usaria:\n\n"
                + "\n".join(self._service_lines())
                + "\n\nCada serviço cotidiano também possui uma aba persistente no Jarvis Desktop. "
                  "Quando possível, uso essa própria aba — inclusive a sessão já autenticada — antes de abrir Google ou outro navegador externo."
            )

        snap = self.snapshot()
        return (
            "Meu runtime atual possui, de forma verificável:\n\n"
            f"- **{snap['actions'].get('actions', 0)} Actions** locais.\n"
            f"- **{snap['workflows'].get('workflows', 0)} Workflows** compostos.\n"
            f"- **{snap['capabilities'].get('capabilities', 0)} capacidades públicas** catalogadas.\n"
            f"- **{snap['services'].get('count', 0)} serviços cotidianos do SindPetshop-SP** mapeados.\n"
            f"- **{snap.get('swarm',{}).get('agents',0)} papéis especialistas** disponíveis no Swarm Intelligence.\n"
            f"- **{snap.get('apprenticeship',{}).get('procedures',0)} rotinas ensinadas** persistentes.\n"
            f"- **{sum(snap.get('acquisition',{}).get('gaps',{}).values()) if snap.get('acquisition') else 0} lacunas de capacidade** registradas pelo Capability Acquisition Engine.\n"
            f"- **{snap.get('acquisition',{}).get('candidates',{}).get('installed',0) if snap.get('acquisition') else 0} competências adquiridas** instaladas por descoberta/composição.\n"
            f"- **{snap.get('long_horizon',{}).get('active',0)} jobs persistentes ativos** no Long-Horizon Runtime.\n"
            f"- **{snap.get('workplace',{}).get('playbooks',0)} playbooks institucionais** no Workplace Intelligence.\n"
            f"- Modelos locais: `{snap['models'].get('fast_model')}` para conversa e `{snap['models'].get('reasoning_model')}` para raciocínio.\n"
            "- Posso combinar memória, Knowledge Base, web/dados públicos, arquivos, navegador, desktop, automações e conectores autorizados.\n\n"
            "Quando você pergunta se eu consigo fazer algo, a resposta vem deste estado real do sistema — não de uma suposição do modelo."
        )
