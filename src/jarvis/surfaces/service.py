from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse
from uuid import uuid4


@dataclass(slots=True)
class _Source:
    title: str
    url: str
    domain: str


class GenerativeSurfaceService:
    """Build trusted, UI-safe surface descriptors from a completed Jarvis answer.

    The model never sends executable HTML. It may produce prose and source metadata;
    this service converts those outputs into a small schema understood by the UI
    registry. This keeps the interface generative without becoming an arbitrary code
    execution channel.
    """

    WEATHER_TERMS = (
        "previsão do tempo", "previsao do tempo", "clima", "tempo hoje",
        "tempo amanhã", "tempo amanha", "temperatura", "vai chover", "chuva hoje",
    )
    NEWS_TERMS = (
        "últimas notícias", "ultimas noticias", "notícias de hoje", "noticias de hoje",
        "notícias", "noticias", "manchetes", "news", "o que aconteceu hoje",
    )
    AGENDA_TERMS = (
        "agenda", "compromissos", "calendário", "calendario", "reuniões", "reunioes",
    )
    INBOX_TERMS = (
        "e-mail", "email", "e-mails", "emails", "caixa de entrada", "inbox",
    )
    AGENT_TERMS = (
        "agentes", "quem está trabalhando", "quem esta trabalhando", "equipe trabalhando",
    )
    SYSTEM_TERMS = (
        "status do sistema", "estado do sistema", "saúde do sistema", "saude do sistema",
        "diagnóstico", "diagnostico", "performance", "desempenho",
    )
    COMPARISON_TERMS = (
        "compare", "comparar", "comparação", "comparacao", "diferença entre", "diferenca entre",
    )
    ANALYTICS_TERMS = (
        "analise estes dados", "analise os dados", "análise dos dados", "analise a planilha",
        "métricas", "metricas", "gráfico", "grafico", "dashboard",
    )

    def build(self, query: str, result: dict) -> list[dict]:
        query = str(query or "").strip()
        content = str((result or {}).get("content") or "").strip()
        metadata = (result or {}).get("metadata") or {}
        kind = str((result or {}).get("kind") or "")
        sources = self._sources(metadata)
        lowered = query.lower()

        surface = None
        if any(term in lowered for term in self.WEATHER_TERMS):
            surface = self._weather(query, content, metadata, sources)
        elif any(term in lowered for term in self.NEWS_TERMS):
            surface = self._news(query, content, sources)
        elif any(term in lowered for term in self.AGENDA_TERMS) or kind == "briefing":
            surface = self._agenda(query, content, metadata, sources)
        elif any(term in lowered for term in self.INBOX_TERMS):
            surface = self._inbox(query, content, metadata, sources)
        elif any(term in lowered for term in self.AGENT_TERMS):
            surface = self._simple("agents", "Atividade dos agentes", content, metadata, sources)
        elif any(term in lowered for term in self.SYSTEM_TERMS):
            surface = self._simple("system", "Estado do Jarvis", content, metadata, sources)
        elif any(term in lowered for term in self.COMPARISON_TERMS):
            surface = self._simple("comparison", "Comparação", content, metadata, sources)
        elif any(term in lowered for term in self.ANALYTICS_TERMS):
            surface = self._simple("analytics", "Análise de dados", content, metadata, sources)
        elif kind in {"delegated", "team_mission", "deep", "hermes"} or sources:
            surface = self._research(query, content, sources, result)

        if not surface:
            return []
        surface.setdefault("surface_id", f"surface-{uuid4().hex[:12]}")
        surface.setdefault("priority", "contextual")
        surface.setdefault("presentation", "surface_primary")
        surface.setdefault("generated_by", "jarvis")
        surface.setdefault("schema_version", 1)
        return [surface]

    def _sources(self, metadata: dict) -> list[_Source]:
        rows = metadata.get("sources") if isinstance(metadata, dict) else None
        if not isinstance(rows, list):
            return []
        out: list[_Source] = []
        seen = set()
        for item in rows:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url") or "").strip()
            if not url or url in seen or not url.startswith(("http://", "https://")):
                continue
            seen.add(url)
            domain = urlparse(url).netloc.removeprefix("www.")
            title = str(item.get("title") or item.get("page_title") or domain or "Fonte").strip()
            out.append(_Source(title=title[:180], url=url[:1000], domain=domain[:120]))
            if len(out) >= 8:
                break
        return out

    @staticmethod
    def _plain(content: str) -> str:
        text = re.sub(r"```[\s\S]*?```", " ", content)
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        text = re.sub(r"^#{1,6}\s*", "", text, flags=re.M)
        text = re.sub(r"[*_>`~]", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _summary(self, content: str, limit: int = 360) -> str:
        plain = self._plain(content)
        marker = plain.lower().find("fontes coletadas pelo jarvis")
        if marker > 0:
            plain = plain[:marker].strip()
        if len(plain) <= limit:
            return plain
        cut = plain[: limit + 1]
        at = max(cut.rfind(". "), cut.rfind("; "), cut.rfind(" — "))
        if at >= max(120, limit // 2):
            cut = cut[: at + 1]
        else:
            cut = cut[:limit].rstrip()
        return cut + "…"

    @staticmethod
    def _bullets(content: str, limit: int = 6) -> list[str]:
        out = []
        for line in str(content or "").splitlines():
            value = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip()
            if value == line.strip() or len(value) < 12:
                continue
            value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
            value = re.sub(r"[*_`#]", "", value).strip()
            if value and value not in out:
                out.append(value[:260])
            if len(out) >= limit:
                break
        return out

    @staticmethod
    def _metric(content: str, labels: tuple[str, ...], value_pattern: str) -> str | None:
        for label in labels:
            match = re.search(
                rf"{label}[^\n.!?]{{0,70}}?({value_pattern})",
                content,
                flags=re.I,
            )
            if match:
                return re.sub(r"\s+", " ", match.group(1)).strip()
        return None

    def _weather(self, query: str, content: str, metadata: dict, sources: list[_Source]) -> dict:
        metrics = []
        structured = metadata.get("weather") if isinstance(metadata, dict) else None
        if isinstance(structured, dict):
            current=structured.get("current") or {}
            today=structured.get("today") or {}
            units=structured.get("units") or {}
            def fmt(value, unit):
                if value is None:return None
                if isinstance(value,float) and value.is_integer():value=int(value)
                return f"{value}{unit}"
            candidates=(
                ("Temperatura",fmt(current.get("temperature"),units.get("temperature","°C"))),
                ("Chuva",fmt(today.get("precipitation_probability_max"),units.get("probability","%"))),
                ("Umidade",fmt(current.get("humidity"),units.get("humidity","%"))),
                ("Vento",fmt(current.get("wind_speed"),units.get("wind_speed","km/h"))),
            )
            metrics.extend({"label":label,"value":value} for label,value in candidates if value is not None)
        if not metrics:
            temp = self._metric(content, (r"temperatura(?: atual)?", r"agora", r"máxima|máxima prevista|maxima"), r"-?\d{1,2}(?:[.,]\d+)?\s*°?\s*C")
            rain = self._metric(content, (r"chuva", r"precipita(?:ção|cao)", r"probabilidade de chuva"), r"\d{1,3}\s*%")
            humidity = self._metric(content, (r"umidade",), r"\d{1,3}\s*%")
            wind = self._metric(content, (r"vento", r"ventos"), r"\d{1,3}(?:[.,]\d+)?\s*(?:km/h|kmh|m/s)")
            for label, value in (("Temperatura", temp), ("Chuva", rain), ("Umidade", humidity), ("Vento", wind)):
                if value:
                    metrics.append({"label": label, "value": value.replace(" °", "°")})
        if not metrics:
            temps = re.findall(r"-?\d{1,2}(?:[.,]\d+)?\s*°\s*C", content, flags=re.I)
            for idx, value in enumerate(dict.fromkeys(temps)):
                metrics.append({"label": "Agora" if idx == 0 else "Referência", "value": value.replace(" ", "")})
                if len(metrics) >= 2:
                    break
        return {
            "surface": "weather",
            "title": "Clima de hoje",
            "subtitle": (structured.get("location") if isinstance(structured,dict) and structured.get("location") else self._query_subject(query, fallback="Previsão resumida")),
            "data": {
                "summary": self._summary(content, 280),
                "metrics": metrics[:4],
                "sources": [self._source_dict(s) for s in sources[:3]],
            },
            "voice_summary": self._summary(content, 320),
            "default_expanded": self._explicit_surface_open(query),
        }

    def _news(self, query: str, content: str, sources: list[_Source]) -> dict:
        items = [
            {"title": s.title, "url": s.url, "source": s.domain}
            for s in sources[:6]
        ]
        if not items:
            items = [{"title": x, "source": "Jarvis"} for x in self._bullets(content, 6)]
        return {
            "surface": "news",
            "title": "Últimas notícias",
            "subtitle": self._query_subject(query, fallback="Atualização em tempo real"),
            "data": {
                "summary": self._summary(content, 300),
                "items": items,
                "sources": [self._source_dict(s) for s in sources[:8]],
                "count": len(items),
            },
            "voice_summary": f"Separei {len(items)} destaques. " + self._summary(content, 220) if items else self._summary(content, 300),
            "default_expanded": self._explicit_surface_open(query),
        }

    def _agenda(self, query: str, content: str, metadata: dict, sources: list[_Source]) -> dict:
        bullets = self._bullets(content, 6)
        items = [{"title": x} for x in bullets]
        return {
            "surface": "agenda",
            "title": "Agenda e prioridades",
            "subtitle": self._query_subject(query, fallback="Seu dia"),
            "data": {
                "summary": self._summary(content, 300),
                "items": items,
                "meta": self._compact_metadata(metadata),
                "sources": [self._source_dict(s) for s in sources[:4]],
            },
            "voice_summary": self._summary(content, 320),
            "default_expanded": False,
        }

    def _inbox(self, query: str, content: str, metadata: dict, sources: list[_Source]) -> dict:
        bullets = self._bullets(content, 6)
        return {
            "surface": "inbox",
            "title": "Caixa de entrada",
            "subtitle": "O que merece atenção",
            "data": {
                "summary": self._summary(content, 300),
                "items": [{"title": x} for x in bullets],
                "meta": self._compact_metadata(metadata),
                "sources": [self._source_dict(s) for s in sources[:4]],
            },
            "voice_summary": self._summary(content, 320),
            "default_expanded": False,
        }

    def _research(self, query: str, content: str, sources: list[_Source], result: dict) -> dict:
        bullets = self._bullets(content, 5)
        return {
            "surface": "research",
            "title": self._research_title(query),
            "subtitle": f"{len(sources)} fonte{'s' if len(sources) != 1 else ''}" if sources else "Síntese Jarvis",
            "data": {
                "summary": self._summary(content, 360),
                "items": [{"title": x} for x in bullets],
                "sources": [self._source_dict(s) for s in sources[:8]],
                "task_id": result.get("task_id"),
                "artifact_id": result.get("artifact_id"),
            },
            "voice_summary": self._summary(content, 320),
            "default_expanded": False,
        }

    def _simple(self, surface: str, title: str, content: str, metadata: dict, sources: list[_Source]) -> dict:
        return {
            "surface": surface,
            "title": title,
            "subtitle": "Contexto vivo",
            "data": {
                "summary": self._summary(content, 320),
                "items": [{"title": x} for x in self._bullets(content, 5)],
                "meta": self._compact_metadata(metadata),
                "sources": [self._source_dict(s) for s in sources[:4]],
            },
            "voice_summary": self._summary(content, 320),
            "default_expanded": False,
        }

    @staticmethod
    def _source_dict(source: _Source) -> dict:
        return {"title": source.title, "url": source.url, "domain": source.domain}

    @staticmethod
    def _compact_metadata(metadata: dict) -> dict:
        if not isinstance(metadata, dict):
            return {}
        keep = ("status", "count", "unread", "events", "priority", "risk")
        return {k: metadata[k] for k in keep if k in metadata and isinstance(metadata[k], (str, int, float, bool))}

    @staticmethod
    def _explicit_surface_open(query: str) -> bool:
        lowered=str(query or '').lower()
        return 'gadget' in lowered and any(x in lowered for x in ('abra','abrir','mostre','mostrar','exiba','expand'))

    @staticmethod
    def _query_subject(query: str, fallback: str) -> str:
        value = " ".join(str(query or "").split()).strip(" ?.!")
        if not value or len(value) > 70:
            return fallback
        return value[:70]

    @staticmethod
    def _research_title(query: str) -> str:
        value = " ".join(str(query or "").split()).strip(" ?.!")
        value = re.sub(r"^(pesquise|pesquisa|investigue|investigar|estude|levante)\s+", "", value, flags=re.I)
        if not value:
            return "Pesquisa Jarvis"
        return value[:72] + ("…" if len(value) > 72 else "")
