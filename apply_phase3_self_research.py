from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENGINE = ROOT / "acquisition" / "engine.py"
COMMANDS = ROOT / "acquisition" / "commands.py"
AGENT = ROOT / "core" / "agent.py"


def replace_once(text, old, new, label):
    if new in text:
        return text, False
    if old not in text:
        raise RuntimeError(
            f"Não encontrei o ponto esperado para {label}. Interrompi sem sobrescrever."
        )
    return text.replace(old, new, 1), True


def patch_engine():
    text = ENGINE.read_text(encoding="utf-8")
    changed = False

    text, c = replace_once(
        text,
        "from urllib.parse import urlparse\n",
        "from urllib.parse import urlparse\nfrom acquisition.self_research import SelfResearchLearner\n",
        "import SelfResearchLearner",
    )
    changed |= c

    text, c = replace_once(
        text,
        "        web_search=None,\n        improvements=None,\n        config=None,\n",
        "        web_search=None,\n        research=None,\n        improvements=None,\n        config=None,\n",
        "parâmetro research",
    )
    changed |= c

    text, c = replace_once(
        text,
        "        self.web_search = web_search\n        self.improvements = improvements\n        self.config = config or {}\n",
        "        self.web_search = web_search\n"
        "        self.research = research\n"
        "        self.improvements = improvements\n"
        "        self.config = config or {}\n"
        "        self.self_research = SelfResearchLearner(\n"
        "            research=self.research, models=self.models, config=self.config\n"
        "        ) if self.research is not None else None\n",
        "inicialização SelfResearch",
    )
    changed |= c

    text, c = replace_once(
        text,
        "    def discover(self, goal, source_url=None, status=None):\n"
        "        result = self.resolve(goal, create_gap=True)\n"
        "        if result.get(\"status\") == \"existing\":\n"
        "            return result\n"
        "        gap_id = result.get(\"gap_id\")\n"
        "        inventory = result.get(\"inventory\") or self.inventory(goal)\n",
        "    def discover(self, goal, source_url=None, status=None, prefer_research=False, research_query=None):\n"
        "        result = self.resolve(goal, create_gap=True)\n"
        "        if result.get(\"status\") == \"existing\" and not prefer_research:\n"
        "            return result\n"
        "        inventory = result.get(\"inventory\") or self.inventory(goal)\n"
        "        gap_id = result.get(\"gap_id\")\n"
        "        if gap_id is None:\n"
        "            gap_id = self._get_or_create_gap(\n"
        "                goal,\n"
        "                \"Pesquisa autônoma solicitada apesar de existir uma competência relacionada.\",\n"
        "            )\n",
        "assinatura discover",
    )
    changed |= c

    anchor = (
        "            candidates.append(candidate)\n"
        "        # 2) Se o usuário forneceu uma URL pública, procurar interfaces padrão.\n"
    )
    inserted = (
        "            candidates.append(candidate)\n\n"
        "        # 1.5) Pesquisa autônoma -> Skill declarativa.\n"
        "        if self.self_research is not None and (prefer_research or not recipe):\n"
        "            try:\n"
        "                learned = self.self_research.learn(\n"
        "                    goal, research_query=research_query, status=status\n"
        "                )\n"
        "            except Exception as exc:\n"
        "                learned = {\"ok\": False, \"error\": str(exc)}\n"
        "            if learned.get(\"ok\"):\n"
        "                skill = learned.get(\"skill\") or {}\n"
        "                candidates.append(self._add_candidate(\n"
        "                    gap_id,\n"
        "                    \"researched_gui_skill\",\n"
        "                    skill.get(\"name\") or \"Skill pesquisada\",\n"
        "                    description=skill.get(\"description\", \"\"),\n"
        "                    source=\"public_web_research\",\n"
        "                    risk=learned.get(\"risk\", \"write\"),\n"
        "                    score=0.88 if learned.get(\"sources\") else 0.72,\n"
        "                    payload={\n"
        "                        \"skill\": skill,\n"
        "                        \"sources\": learned.get(\"sources\", []),\n"
        "                        \"research_query\": learned.get(\"query\"),\n"
        "                    },\n"
        "                ))\n"
        "            else:\n"
        "                self._event(\n"
        "                    \"self_research_failed\", gap_id=gap_id,\n"
        "                    error=str(learned.get(\"error\") or \"falha\")[:900],\n"
        "                    issues=learned.get(\"issues\", []),\n"
        "                )\n\n"
        "        # 2) Se o usuário forneceu uma URL pública, procurar interfaces padrão.\n"
    )
    text, c = replace_once(text, anchor, inserted, "bloco SelfResearch")
    changed |= c

    text, c = replace_once(
        text,
        "        if kind == \"recipe\":\n"
        "            check = self.validate_recipe((payload.get(\"recipe\") or {}))\n"
        "        elif kind == \"openapi_import\":\n",
        "        if kind == \"recipe\":\n"
        "            check = self.validate_recipe((payload.get(\"recipe\") or {}))\n"
        "        elif kind == \"researched_gui_skill\":\n"
        "            check = (\n"
        "                self.self_research.validate_skill(payload.get(\"skill\") or {})\n"
        "                if self.self_research is not None\n"
        "                else {\"ok\": False, \"error\": \"Self-Research indisponível.\"}\n"
        "            )\n"
        "        elif kind == \"openapi_import\":\n",
        "teste de candidato pesquisado",
    )
    changed |= c

    text, c = replace_once(
        text,
        "            installed_id = (result or {}).get(\"name\", \"\")\n"
        "        elif kind == \"openapi_import\":\n",
        "            installed_id = (result or {}).get(\"name\", \"\")\n"
        "        elif kind == \"researched_gui_skill\":\n"
        "            skill = payload.get(\"skill\") or {}\n"
        "            checked = (\n"
        "                self.self_research.validate_skill(skill)\n"
        "                if self.self_research is not None else {\"ok\": False}\n"
        "            )\n"
        "            if not checked.get(\"ok\"):\n"
        "                return {\"ok\": False, \"error\": \"Skill pesquisada não passou na validação final.\", \"validation\": checked}\n"
        "            normalized = checked.get(\"skill\") or skill\n"
        "            result = self.skills.save_parametric_skill(\n"
        "                normalized.get(\"name\") or candidate.get(\"title\"),\n"
        "                normalized.get(\"steps\") or [],\n"
        "                inputs=normalized.get(\"inputs\") or {},\n"
        "                description=normalized.get(\"description\") or candidate.get(\"description\", \"\"),\n"
        "                metadata={\n"
        "                    \"acquired_by\": \"SelfResearchLearner\",\n"
        "                    \"candidate_id\": int(candidate_id),\n"
        "                    \"gap_id\": candidate.get(\"gap_id\"),\n"
        "                    \"source\": \"public_web_research\",\n"
        "                    \"sources\": payload.get(\"sources\", []),\n"
        "                    \"research_query\": payload.get(\"research_query\"),\n"
        "                    \"risk\": candidate.get(\"risk\"),\n"
        "                    \"confidence\": candidate.get(\"score\"),\n"
        "                    \"validated\": True,\n"
        "                    \"verification\": normalized.get(\"verification\") or {},\n"
        "                },\n"
        "            )\n"
        "            installed_id = (result or {}).get(\"name\", \"\")\n"
        "        elif kind == \"openapi_import\":\n",
        "instalação de candidato pesquisado",
    )
    changed |= c

    text, c = replace_once(
        text,
        "            \"installed_id\": installed_id,\n"
        "            \"result\": result,\n"
        "        }\n",
        "            \"installed_id\": installed_id,\n"
        "            \"result\": result,\n"
        "            \"example_inputs\": (\n"
        "                ((payload.get(\"skill\") or {}).get(\"example_inputs\") or {})\n"
        "                if kind == \"researched_gui_skill\" else {}\n"
        "            ),\n"
        "            \"verification\": (\n"
        "                ((payload.get(\"skill\") or {}).get(\"verification\") or {})\n"
        "                if kind == \"researched_gui_skill\" else {}\n"
        "            ),\n"
        "            \"sources\": payload.get(\"sources\", []) if kind == \"researched_gui_skill\" else [],\n"
        "        }\n",
        "retorno de instalação",
    )
    changed |= c

    if changed:
        ENGINE.write_text(text, encoding="utf-8")
    return changed


def patch_commands():
    text = COMMANDS.read_text(encoding="utf-8")
    changed = False

    anchor = "    discover_patterns = (\n"
    block = (
        "    # Pesquisa pública + tentativa explícita.\n"
        "    research_try_patterns = (\n"
        "        r\"^(?:pesquise|procure|investigue)\\s+como\\s+(?:faz(?:er)?(?:\\s+para)?|realizar)\\s+(.+?)\\s+e\\s+(?:tente|procure)\\s+(?:fazer|realizar|executar)?\\s*(.+)$\",\n"
        "        r\"^(?:pesquise|procure|investigue)\\s+como\\s+(.+?)\\s+e\\s+(?:tente|procure)\\s+(.+)$\",\n"
        "    )\n"
        "    for pattern in research_try_patterns:\n"
        "        m = re.match(pattern, raw, flags=re.I)\n"
        "        if m:\n"
        "            first = m.group(1).strip()\n"
        "            second = m.group(2).strip()\n"
        "            url = URL_RE.search(raw)\n"
        "            return {\n"
        "                \"action\": \"discover\",\n"
        "                \"goal\": second or first,\n"
        "                \"research_query\": first,\n"
        "                \"source_url\": url.group(0).rstrip(\".,;\") if url else None,\n"
        "                \"auto_install\": True,\n"
        "                \"auto_try\": True,\n"
        "                \"prefer_research\": True,\n"
        "            }\n\n"
        "    research_only_patterns = (\n"
        "        r\"^(?:pesquise|procure|investigue)\\s+como\\s+(?:faz(?:er)?(?:\\s+para)?|realizar)\\s+(.+)$\",\n"
        "        r\"^(?:pesquise|procure|investigue)\\s+como\\s+(.+)$\",\n"
        "    )\n"
        "    for pattern in research_only_patterns:\n"
        "        m = re.match(pattern, raw, flags=re.I)\n"
        "        if m:\n"
        "            goal = m.group(1).strip()\n"
        "            url = URL_RE.search(raw)\n"
        "            return {\n"
        "                \"action\": \"discover\",\n"
        "                \"goal\": goal,\n"
        "                \"research_query\": goal,\n"
        "                \"source_url\": url.group(0).rstrip(\".,;\") if url else None,\n"
        "                \"auto_install\": False,\n"
        "                \"auto_try\": False,\n"
        "                \"prefer_research\": True,\n"
        "            }\n\n"
    )
    if block not in text:
        if anchor not in text:
            raise RuntimeError("Não encontrei discover_patterns.")
        text = text.replace(anchor, block + anchor, 1)
        changed = True

    old = (
        '                "auto_install": True,\n'
        "            }\n"
        "    patterns = (\n"
    )
    new = (
        '                "auto_install": True,\n'
        '                "auto_try": False,\n'
        '                "prefer_research": True,\n'
        '                "research_query": m.group(1).strip(),\n'
        "            }\n"
        "    patterns = (\n"
    )
    if new not in text:
        if old not in text:
            raise RuntimeError("Não encontrei learn_patterns para ampliar.")
        text = text.replace(old, new, 1)
        changed = True

    if changed:
        COMMANDS.write_text(text, encoding="utf-8")
    return changed


def patch_agent():
    text = AGENT.read_text(encoding="utf-8")
    changed = False

    text, c = replace_once(
        text,
        "            web_search=self.web_search,\n            improvements=self.improvements,\n",
        "            web_search=self.web_search,\n            research=self.research,\n            improvements=self.improvements,\n",
        "ResearchEngine no CapabilityAcquisition",
    )
    changed |= c

    text, c = replace_once(
        text,
        "                    source_url=acquisition_cmd.get(\"source_url\"),\n"
        "                    status=status,\n"
        "                )\n",
        "                    source_url=acquisition_cmd.get(\"source_url\"),\n"
        "                    status=status,\n"
        "                    prefer_research=bool(acquisition_cmd.get(\"prefer_research\")),\n"
        "                    research_query=acquisition_cmd.get(\"research_query\"),\n"
        "                )\n",
        "parâmetros discover",
    )
    changed |= c

    text, c = replace_once(
        text,
        "                    safe = next((\n"
        "                        x for x in result.get(\"candidates\", [])\n"
        "                        if x.get(\"kind\") == \"recipe\" and x.get(\"risk\") in {\"read\", \"read_only\", \"act\"}\n"
        "                    ), None)\n",
        "                    allowed_risks = {\"read\", \"read_only\", \"act\"}\n"
        "                    if acquisition_cmd.get(\"auto_try\"):\n"
        "                        allowed_risks.add(\"write\")\n"
        "                    options = [\n"
        "                        x for x in result.get(\"candidates\", [])\n"
        "                        if x.get(\"kind\") in {\"recipe\", \"researched_gui_skill\"}\n"
        "                        and x.get(\"risk\") in allowed_risks\n"
        "                    ]\n"
        "                    options.sort(key=lambda x: (\n"
        "                        0 if x.get(\"kind\") == \"researched_gui_skill\" and acquisition_cmd.get(\"prefer_research\") else 1,\n"
        "                        -float(x.get(\"score\", 0)),\n"
        "                    ))\n"
        "                    safe = options[0] if options else None\n",
        "seleção de candidato",
    )
    changed |= c

    text, c = replace_once(
        text,
        "                        if installed.get(\"ok\"):\n"
        "                            return (\n"
        "                                self.summarize(\"install_capability_candidate\", installed)\n"
        "                                + \"\\n\\nA competência foi criada apenas com ferramentas já confiáveis do meu runtime.\"\n"
        "                            )\n",
        "                        if installed.get(\"ok\"):\n"
        "                            if acquisition_cmd.get(\"auto_try\") and installed.get(\"installed_id\"):\n"
        "                                if status:\n"
        "                                    status(\"Autoaprendizado: testando a nova capacidade\")\n"
        "                                attempt = self.dispatch(\n"
        "                                    \"run_skill\",\n"
        "                                    {\"name\": installed.get(\"installed_id\"), \"inputs\": installed.get(\"example_inputs\") or {}},\n"
        "                                    confirm_callback=confirm_callback,\n"
        "                                    source=\"self_research_auto_try\",\n"
        "                                )\n"
        "                                self._last_response_metadata = {\n"
        "                                    \"grounded\": True,\n"
        "                                    \"capability_acquisition\": True,\n"
        "                                    \"self_research\": True,\n"
        "                                    \"execution_attempted\": True,\n"
        "                                    \"execution_ok\": bool(attempt.get(\"ok\")),\n"
        "                                    \"external_effect_verified\": False,\n"
        "                                    \"sources\": installed.get(\"sources\") or [],\n"
        "                                }\n"
        "                                if attempt.get(\"ok\"):\n"
        "                                    return (\n"
        "                                        f\"Pesquisei fontes públicas, aprendi a capacidade ‘{installed.get('installed_id')}’ e executei uma tentativa. \"\n"
        "                                        \"A sequência terminou sem erro técnico, mas ainda não tenho evidência suficiente para afirmar que o efeito externo foi concluído. \"\n"
        "                                        \"Não vou declarar sucesso sem verificação.\"\n"
        "                                    )\n"
        "                                return (\n"
        "                                    f\"Pesquisei e aprendi a capacidade ‘{installed.get('installed_id')}’, mas a tentativa falhou: \"\n"
        "                                    f\"{attempt.get('error') or 'falha durante a execução da Skill'}.\"\n"
        "                                )\n"
        "                            return (\n"
        "                                self.summarize(\"install_capability_candidate\", installed)\n"
        "                                + \"\\n\\nA competência foi criada apenas com ferramentas já confiáveis do meu runtime.\"\n"
        "                            )\n",
        "auto tentativa",
    )
    changed |= c

    text, c = replace_once(
        text,
        "- Nunca declare sucesso quando uma ferramenta falhou.\n",
        "- Nunca declare sucesso quando uma ferramenta falhou.\n"
        "- Executar cliques, digitação ou uma Skill sem erro NÃO prova que um efeito externo ocorreu; "
        "só declare envio, publicação ou alteração concluída quando houver evidência verificável do estado final.\n",
        "princípio de verificação",
    )
    changed |= c

    text, c = replace_once(
        text,
        '        if any(k in text for k in ["aprenda sozinho","descubra como","adquira capacidade","não sabe fazer","nao sabe fazer","não consigo fazer","nao consigo fazer","o que falta para","nova capacidade","nova competência","nova competencia"]):\n',
        '        if any(k in text for k in ["aprenda sozinho","descubra como","pesquise como","procure como","investigue como","adquira capacidade","não sabe fazer","nao sabe fazer","não consigo fazer","nao consigo fazer","o que falta para","nova capacidade","nova competência","nova competencia"]):\n',
        "roteamento self-research",
    )
    changed |= c

    if changed:
        AGENT.write_text(text, encoding="utf-8")
    return changed


def main():
    for p in (ENGINE, COMMANDS, AGENT):
        if not p.exists():
            raise SystemExit(f"Arquivo não encontrado: {p.relative_to(ROOT)}")

    results = {
        "acquisition/engine.py": patch_engine(),
        "acquisition/commands.py": patch_commands(),
        "core/agent.py": patch_agent(),
    }

    print("Phase 3 — Self-Research + Verified Execution aplicada.")
    for name, changed in results.items():
        print(f"- {name}: {'alterado' if changed else 'já estava atualizado'}")


if __name__ == "__main__":
    main()
