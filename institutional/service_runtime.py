import re


class InstitutionalServiceRuntime:
    """Deterministic first-hop for known daily services, before heavy Agent Runtime."""

    ANALYSIS_VERBS = (
        "veja", "verifique", "analise", "analisar", "consulte", "acesse",
        "leia", "avalie", "confira", "olhe", "examine", "use", "utilize",
        "pegue", "extraia", "busque", "pesquise", "compare", "ver", "cheque"
    )

    def __init__(self, services, browser, models):
        self.services = services
        self.browser = browser
        self.models = models

    def resolve_from_text(self, text):
        t = str(text or "").lower()
        candidates = []
        for item in self.services.items:
            aliases = [item.get("id", ""), item.get("name", "")] + list(item.get("aliases", []))
            for alias in aliases:
                a = str(alias or "").strip().lower()
                if a and a in t:
                    candidates.append((len(a), item))
                    break
        if not candidates:
            return None
        candidates.sort(key=lambda x: -x[0])
        return candidates[0][1]

    def matches(self, text):
        item = self.resolve_from_text(text)
        if not item:
            return False
        t = str(text or "").lower()
        return any(v in t for v in self.ANALYSIS_VERBS)

    def _looks_authenticated(self, inspection):
        text = str(inspection.get("text") or "").lower()
        markers = ("sign in", "log in", "login", "entrar", "senha", "password")
        # This is only a heuristic. It must never claim authentication with certainty.
        return not any(m in text[:3500] for m in markers)

    def _fallback(self, item, inspection, error=None):
        hints = item.get("analysis_hints") or []
        lines = [
            f"Consegui identificar **{item.get('name')}** como a ferramenta correta para esta tarefa."
        ]
        if inspection and inspection.get("ok"):
            title = inspection.get("title") or "página carregada"
            lines.append(f"A página está disponível no Jarvis (`{title}`).")
            headings = [x.get("text") for x in inspection.get("headings", []) if x.get("text")]
            if headings:
                lines.append("Seções visíveis detectadas: " + ", ".join(headings[:8]) + ".")
        elif error:
            lines.append(f"O Browser Agent não conseguiu ler a página agora: {error}")

        if hints:
            lines.append("\nAntes de decidir a próxima publicação, eu analisaria principalmente:")
            lines.extend(f"- {x}" for x in hints)
        else:
            lines.append("\nPosso usar esta ferramenta quando a sessão e os dados necessários estiverem disponíveis.")
        lines.append(f"\nFonte/ferramenta: {item.get('url')}")
        return "\n".join(lines)

    def run(self, user_text, status=None):
        item = self.resolve_from_text(user_text)
        if not item:
            return {"ok": False, "error": "Serviço institucional não identificado."}

        if status:
            status(f"Consultando {item.get('name')}")

        # Mantém a ferramenta correta visível dentro do próprio Jarvis.
        try:
            self.services.open(item.get("id"))
        except Exception:
            pass

        inspection = None
        embedded_error = None

        # Preferir a aba embutida é importante para serviços autenticados:
        # a mesma sessão que o usuário abriu manualmente pode ser lida pelo Jarvis.
        try:
            inspection = self.services.tab_action(
                item.get("id"), "inspect", max_chars=14000
            )
            if not inspection.get("ok"):
                embedded_error = inspection.get("error")
                inspection = None
        except Exception as exc:
            embedded_error = str(exc)
            inspection = None

        # Browser Agent continua como fallback para serviços públicos ou quando a
        # interface desktop não está disponível.
        if not inspection:
            try:
                inspection = self.browser.inspect_page(
                    item.get("url"), wait_ms=1600, max_chars=14000
                )
            except Exception as exc:
                return {
                    "ok": True,
                    "answer": self._fallback(item, {}, embedded_error or str(exc)),
                    "service": item,
                    "source": item.get("url"),
                    "fallback": True,
                    "grounded": False,
                }

        visible = str(inspection.get("text") or "").strip()
        # Authenticated/private services can still be opened, but we avoid inventing their contents.
        if item.get("access") in {"private_browser_session", "browser_session"} and not self._looks_authenticated(inspection):
            return {
                "ok": True,
                "answer": (
                    f"Abri **{item.get('name')}**, mas a página parece estar pedindo autenticação. "
                    "Faça o login manualmente no navegador do Jarvis e depois repita o pedido. "
                    "Eu não armazeno nem preencho sua senha."
                ),
                "service": item,
                "source": item.get("url"),
                "fallback": True,
                "grounded": True,
            }

        if len(visible) < 80:
            return {
                "ok": True,
                "answer": self._fallback(item, inspection),
                "service": item,
                "source": item.get("url"),
                "fallback": True,
                "grounded": True,
            }

        hints = "\n".join(f"- {x}" for x in item.get("analysis_hints", []))
        prompt = (
            "Você é Jarvis. Responda em português e seja objetivo.\n"
            "O usuário pediu uma análise de uma ferramenta real do ambiente de trabalho.\n"
            "Use APENAS o conteúdo visível coletado abaixo para afirmar métricas/fatos; se algo não estiver visível, diga isso.\n"
            "Não invente valores. Não explique infraestrutura técnica.\n\n"
            f"PEDIDO DO USUÁRIO:\n{user_text}\n\n"
            f"FERRAMENTA: {item.get('name')}\nURL: {inspection.get('url')}\n"
            f"FOCOS RECOMENDADOS:\n{hints or '- identificar informações úteis ao objetivo'}\n\n"
            f"CONTEÚDO VISÍVEL DA PÁGINA:\n{visible[:8500]}"
        )
        try:
            response = self.models.chat(
                messages=[
                    {"role": "system", "content": "Analise evidência de interface sem inventar dados."},
                    {"role": "user", "content": prompt},
                ],
                user_text=user_text,
                force="fast",
            )
            content = ((response.get("message") or {}).get("content") or "").strip()
            content = re.sub(r"<think>.*?</think>", "", content, flags=re.I | re.S).strip()
            if content:
                return {
                    "ok": True,
                    "answer": content,
                    "model": response.get("_jarvis_model"),
                    "service": item,
                    "source": inspection.get("url") or item.get("url"),
                    "fallback": False,
                    "grounded": True,
                }
        except Exception as exc:
            return {
                "ok": True,
                "answer": self._fallback(item, inspection, str(exc)),
                "service": item,
                "source": inspection.get("url") or item.get("url"),
                "fallback": True,
                "grounded": True,
            }

        return {
            "ok": True,
            "answer": self._fallback(item, inspection),
            "service": item,
            "source": inspection.get("url") or item.get("url"),
            "fallback": True,
            "grounded": True,
        }
