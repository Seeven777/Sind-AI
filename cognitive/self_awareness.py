class SelfAwareness:
    """Grounded self-knowledge from the actual runtime, not model imagination."""

    def __init__(self, services, actions, workflows, capabilities, models, hardware, knowledge, connectors=None):
        self.services = services
        self.actions = actions
        self.workflows = workflows
        self.capabilities = capabilities
        self.models = models
        self.hardware = hardware
        self.knowledge = knowledge
        self.connectors = connectors

    def matches(self, text):
        t = str(text or "").lower().strip()
        patterns = (
            "o que você consegue", "o que voce consegue", "o que você sabe fazer", "o que voce sabe fazer",
            "quais ferramentas", "quais sistemas", "quais serviços", "quais servicos",
            "você consegue acessar", "voce consegue acessar", "você tem acesso", "voce tem acesso",
            "quais recursos", "suas capacidades", "suas ferramentas",
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
                + "\n\nEu escolho entre eles pelo objetivo da tarefa. Eles não precisam virar abas da interface."
            )

        snap = self.snapshot()
        return (
            "Meu runtime atual possui, de forma verificável:\n\n"
            f"- **{snap['actions'].get('actions', 0)} Actions** locais.\n"
            f"- **{snap['workflows'].get('workflows', 0)} Workflows** compostos.\n"
            f"- **{snap['capabilities'].get('capabilities', 0)} capacidades públicas** catalogadas.\n"
            f"- **{snap['services'].get('count', 0)} serviços cotidianos do SindPetshop-SP** mapeados.\n"
            f"- Modelos locais: `{snap['models'].get('fast_model')}` para conversa e `{snap['models'].get('reasoning_model')}` para raciocínio.\n"
            "- Posso combinar memória, Knowledge Base, web/dados públicos, arquivos, navegador, desktop, automações e conectores autorizados.\n\n"
            "Quando você pergunta se eu consigo fazer algo, a resposta vem deste estado real do sistema — não de uma suposição do modelo."
        )
