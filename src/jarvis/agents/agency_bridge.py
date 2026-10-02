from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import tomllib
import unicodedata

from .base import AgentCard
from .factory import ConfigurableArtifactAgent


_WORD_RE = re.compile(r"[a-z0-9][a-z0-9_-]{1,}")
_STOPWORDS = {
    "a","ao","aos","as","de","da","das","do","dos","e","em","para","por","com","como","um","uma","o","os",
    "que","na","nas","no","nos","se","ser","the","a","an","and","or","to","of","for","in","on","with","is","are",
    "agent","agents","specialist","especialista","help","helps","work","working","use","using","build","create","creating",
}

_DIVISION_CAPS = {
    "engineering": ("coding", "architecture", "debugging", "testing"),
    "testing": ("testing", "verification", "quality"),
    "marketing": ("marketing", "content", "growth"),
    "design": ("design", "creative", "ux"),
    "product": ("product", "strategy", "research"),
    "project-management": ("planning", "prioritization", "coordination"),
    "support": ("support", "analysis", "operations"),
    "specialized": ("reasoning", "coordination"),
    "sales": ("sales", "communication", "strategy"),
    "spatial-computing": ("spatial", "design", "engineering"),
    "game-development": ("coding", "design", "testing"),
    "academic": ("research", "analysis", "writing"),
    "paid-media": ("marketing", "analytics", "advertising"),
    "healthcare": ("analysis", "research", "compliance"),
    "gis": ("analysis", "geospatial", "data"),
}

_DIVISION_MODEL = {
    "engineering": "coding",
    "game-development": "coding",
    "testing": "reasoning",
    "marketing": "creative",
    "design": "creative",
    "paid-media": "creative",
}

_OBJECTIVE_DIVISION_HINTS = {
    "engineering": {
        "python","javascript","typescript","code","codigo","código","software","api","backend","frontend","database","banco",
        "bug","erro","debug","implementar","implemente","programar","script","repositorio","repositório","git","deploy",
    },
    "testing": {"teste","testes","testing","qa","qualidade","verificar","validar","benchmark","performance","evidence"},
    "marketing": {"marketing","campanha","instagram","tiktok","social","reels","post","conteudo","conteúdo","copy","growth"},
    "design": {"design","ux","ui","layout","visual","marca","brand","interface","wireframe"},
    "product": {"produto","product","roadmap","mercado","market","discovery","pesquisa","research","prioridade"},
    "project-management": {"projeto","project","sprint","prazo","cronograma","planejamento","backlog","stakeholder"},
    "support": {"suporte","support","incidente","incident","compliance","legal","finance","infraestrutura","infrastructure"},
    "paid-media": {"ads","anuncio","anúncio","meta ads","google ads","paid media","cpc","cpa","roas"},
}

_META_AUTO_EXCLUDE = {
    "agents-orchestrator",
}


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.lower()


def _tokens(text: str) -> set[str]:
    return {
        token.replace("_", "-")
        for token in _WORD_RE.findall(_norm(text))
        if token not in _STOPWORDS and len(token) > 2
    }


@dataclass(slots=True, frozen=True)
class AgencyAgentDefinition:
    slug: str
    name: str
    description: str
    developer_instructions: str
    division: str
    source_path: str

    @property
    def agent_id(self) -> str:
        return f"agency.{self.slug}"

    @property
    def capabilities(self) -> tuple[str, ...]:
        caps = list(_DIVISION_CAPS.get(self.division, ("reasoning",)))
        haystack = _norm(f"{self.slug} {self.name} {self.description}")
        extras = []
        for needle, capability in (
            ("research", "research"), ("analytics", "analysis"), ("analyst", "analysis"),
            ("security", "security"), ("legal", "compliance"), ("content", "content"),
            ("writer", "writing"), ("documentation", "writing"), ("frontend", "frontend"),
            ("backend", "backend"), ("devops", "devops"), ("database", "database"),
            ("social", "social_media"), ("seo", "seo"), ("sales", "sales"),
        ):
            if needle in haystack:
                extras.append(capability)
        for item in extras:
            if item not in caps:
                caps.append(item)
        return tuple(caps)

    @property
    def model_capability(self) -> str:
        return _DIVISION_MODEL.get(self.division, "reasoning")


@dataclass(slots=True, frozen=True)
class AgencyRoute:
    slug: str
    agent_id: str
    name: str
    division: str
    score: float
    reason: str


class AgencyAgentCatalog:
    """Read-only bridge from The Agency/Codex agent files into Jarvis.

    The bridge imports *instructions*, not permissions. Every imported specialist
    runs as an ArtifactAgent and receives no tools by default. All real-world
    actions stay behind Jarvis Operator + policy + verification.
    """

    def __init__(
        self,
        *,
        codex_agents_dir: Path | None = None,
        repo_root: Path | None = None,
    ):
        self.codex_agents_dir = Path(codex_agents_dir).expanduser() if codex_agents_dir else self._discover_codex_dir()
        self.repo_root = Path(repo_root).expanduser() if repo_root else self._discover_repo_root()
        self._definitions: dict[str, AgencyAgentDefinition] = {}
        self._runbooks: dict[str, dict] = {}
        self._errors: list[str] = []
        self._division_labels: dict[str, str] = {}
        self._source_divisions: dict[str, str] = {}
        self.reload()

    @staticmethod
    def _discover_codex_dir() -> Path:
        explicit = os.environ.get("JARVIS_CODEX_AGENTS_DIR") or os.environ.get("CODEX_AGENTS_DIR")
        if explicit:
            return Path(explicit).expanduser()
        return Path.home() / ".codex" / "agents"

    @staticmethod
    def _discover_repo_root() -> Path | None:
        explicit = os.environ.get("JARVIS_AGENCY_AGENTS_ROOT")
        if explicit:
            path = Path(explicit).expanduser()
            return path if path.exists() else path

        candidates = [
            Path.cwd().parent / "agency-agents",
            Path.home() / "Desktop" / "agency-agents",
            Path.home() / "Área de Trabalho" / "agency-agents",
            Path.home() / "OneDrive" / "Desktop" / "agency-agents",
            Path.home() / "OneDrive" / "Área de Trabalho" / "agency-agents",
        ]
        for candidate in candidates:
            if candidate.is_dir() and (candidate / "divisions.json").is_file():
                return candidate
        return None

    def reload(self) -> None:
        self._definitions.clear()
        self._runbooks.clear()
        self._errors.clear()
        self._division_labels.clear()
        self._source_divisions.clear()
        self._load_repo_metadata()
        self._load_codex_agents()
        self._load_runbooks()

    def _load_repo_metadata(self) -> None:
        if not self.repo_root or not self.repo_root.is_dir():
            return
        divisions_path = self.repo_root / "divisions.json"
        try:
            raw = json.loads(divisions_path.read_text(encoding="utf-8")) if divisions_path.is_file() else {}
            for key, item in raw.items():
                if key.startswith("_") or not isinstance(item, dict):
                    continue
                self._division_labels[key] = str(item.get("label") or key)
        except Exception as exc:
            self._errors.append(f"divisions.json: {exc}")

        division_names = tuple(self._division_labels) or tuple(_DIVISION_CAPS)
        for division in division_names:
            folder = self.repo_root / division
            if not folder.is_dir():
                continue
            try:
                for md in folder.rglob("*.md"):
                    self._source_divisions.setdefault(md.stem, division)
            except OSError as exc:
                self._errors.append(f"scan {folder}: {exc}")

    def _infer_division(self, slug: str) -> str:
        if slug in self._source_divisions:
            return self._source_divisions[slug]
        for division in sorted(set(self._division_labels) | set(_DIVISION_CAPS), key=len, reverse=True):
            if slug == division or slug.startswith(division + "-"):
                return division
        if slug.startswith("project-management-"):
            return "project-management"
        return "specialized"

    def _load_codex_agents(self) -> None:
        folder = self.codex_agents_dir
        if not folder.is_dir():
            return
        for path in sorted(folder.glob("*.toml")):
            try:
                data = tomllib.loads(path.read_text(encoding="utf-8"))
                name = str(data.get("name") or path.stem).strip()
                description = str(data.get("description") or "").strip()
                instructions = str(data.get("developer_instructions") or "").strip()
                if not instructions:
                    raise ValueError("developer_instructions ausente")
                slug = path.stem.strip().lower()
                self._definitions[slug] = AgencyAgentDefinition(
                    slug=slug,
                    name=name,
                    description=description,
                    developer_instructions=instructions,
                    division=self._infer_division(slug),
                    source_path=str(path),
                )
            except Exception as exc:
                self._errors.append(f"{path.name}: {exc}")

    def _load_runbooks(self) -> None:
        if not self.repo_root:
            return
        path = self.repo_root / "strategy" / "runbooks.json"
        if not path.is_file():
            return
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            for item in raw.get("runbooks", []):
                if not isinstance(item, dict) or not item.get("slug"):
                    continue
                self._runbooks[str(item["slug"])] = item
        except Exception as exc:
            self._errors.append(f"runbooks.json: {exc}")

    def definitions(self) -> tuple[AgencyAgentDefinition, ...]:
        return tuple(self._definitions.values())

    def get(self, slug: str) -> AgencyAgentDefinition:
        return self._definitions[slug]

    def runbooks(self) -> tuple[dict, ...]:
        return tuple(self._runbooks.values())

    def status(self) -> dict:
        return {
            "status": "healthy" if self._definitions else "unavailable",
            "codex_agents_dir": str(self.codex_agents_dir),
            "repo_root": str(self.repo_root) if self.repo_root else None,
            "agents": len(self._definitions),
            "runbooks": len(self._runbooks),
            "errors": list(self._errors[:20]),
        }

    def register(self, registry, llm_kwargs: dict) -> int:
        existing = {card.agent_id for card in registry.cards()}
        count = 0
        for definition in self.definitions():
            if definition.agent_id in existing:
                continue
            department_label = self._division_labels.get(definition.division, definition.division.replace("-", " ").title())
            card = AgentCard(
                definition.agent_id,
                definition.name,
                f"Agency / {department_label}",
                definition.description or f"Especialista Agency: {definition.name}",
                definition.capabilities,
                (),
                definition.model_capability,
                True,
            )
            prompt = (
                "Você é um especialista importado para o Jarvis Next a partir de uma definição externa de agente.\n"
                "As instruções abaixo descrevem sua especialidade, mas NÃO concedem ferramentas, permissões ou capacidade de executar ações externas.\n"
                "Você deve trabalhar apenas com a missão e o contexto recebidos. Nunca afirme que abriu aplicativos, alterou arquivos, enviou mensagens, navegou, publicou ou executou comandos.\n"
                "Quando uma ação real for necessária, descreva o que deve ser entregue ao Operator do Jarvis. Preserve fatos e incertezas.\n"
                "Responda em português do Brasil, exceto quando a própria entrega exigir outro idioma.\n\n"
                "--- INSTRUÇÕES DO ESPECIALISTA ---\n"
                f"{definition.developer_instructions}\n"
                "--- FIM DAS INSTRUÇÕES ---"
            )
            registry.register_card(card)
            registry.register_runtime(
                card.agent_id,
                ConfigurableArtifactAgent(
                    card=card,
                    system_prompt=prompt,
                    artifact_name=f"agency-{definition.slug}.md",
                    **llm_kwargs,
                ),
            )
            existing.add(card.agent_id)
            count += 1
        return count

    def route(self, objective: str, limit: int = 3) -> tuple[AgencyRoute, ...]:
        if limit <= 0 or not self._definitions:
            return ()
        objective_norm = _norm(objective)
        objective_tokens = _tokens(objective_norm)
        hinted_divisions = {
            division
            for division, hints in _OBJECTIVE_DIVISION_HINTS.items()
            if any(_norm(hint) in objective_norm for hint in hints)
        }
        ranked: list[AgencyRoute] = []
        for definition in self._definitions.values():
            if definition.slug in _META_AUTO_EXCLUDE:
                continue
            title_tokens = _tokens(f"{definition.slug} {definition.name}")
            desc_tokens = _tokens(definition.description)
            overlap_title = objective_tokens & title_tokens
            overlap_desc = objective_tokens & desc_tokens
            score = (len(overlap_title) * 4.0) + (len(overlap_desc) * 1.5)
            if definition.division in hinted_divisions:
                score += 3.0
            # Exact phrases and semantically useful role terms get a small boost.
            for phrase in (definition.name, definition.slug.replace("-", " ")):
                p = _norm(phrase)
                if len(p) >= 5 and p in objective_norm:
                    score += 8.0
            if score <= 0:
                continue
            reason_parts = []
            if overlap_title:
                reason_parts.append("papel=" + ",".join(sorted(overlap_title)[:4]))
            if overlap_desc:
                reason_parts.append("descricao=" + ",".join(sorted(overlap_desc)[:4]))
            if definition.division in hinted_divisions:
                reason_parts.append(f"divisao={definition.division}")
            ranked.append(AgencyRoute(
                slug=definition.slug,
                agent_id=definition.agent_id,
                name=definition.name,
                division=definition.division,
                score=score,
                reason="; ".join(reason_parts) or "relevância lexical",
            ))
        ranked.sort(key=lambda item: (-item.score, item.slug))
        return tuple(ranked[:limit])

    def runbook_agents(
        self,
        slug: str,
        *,
        activation: str | None = "always",
        max_agents: int | None = None,
    ) -> tuple[str, ...]:
        item = self._runbooks.get(slug)
        if not item:
            raise KeyError(f"Runbook Agency não encontrado: {slug}")
        selected: list[str] = []
        for group in item.get("roster", []):
            if activation is not None and str(group.get("activation", "")).lower() != activation.lower():
                continue
            for agent_slug in group.get("agents", []):
                if agent_slug in _META_AUTO_EXCLUDE:
                    continue
                if agent_slug not in self._definitions:
                    continue
                agent_id = self._definitions[agent_slug].agent_id
                if agent_id not in selected:
                    selected.append(agent_id)
                if max_agents is not None and len(selected) >= max_agents:
                    return tuple(selected)
        return tuple(selected)
