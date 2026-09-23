import json
import re
import sqlite3
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


RISK_ORDER = {
    "read": 0,
    "read_only": 0,
    "act": 1,
    "write": 2,
    "high": 3,
    "critical": 4,
}


class CapabilityAcquisitionEngine:
    """
    Descobre como o Jarvis pode adquirir uma competência que ainda não possui.

    A engine NÃO executa código arbitrário gerado pelo modelo. Uma competência
    adquirida é preferencialmente uma receita declarativa composta por Actions,
    Workflows, Capabilities, Skills ou serviços que já existem no runtime.

    APIs públicas OpenAPI podem ser importadas apenas pelo importer já seguro do
    CapabilityHub (HTTPS público, GET anônimo e sem autenticação).
    """

    def __init__(
        self,
        db_path,
        models,
        skills,
        apprenticeship,
        actions,
        workflows,
        capabilities,
        public_data,
        services,
        web_search=None,
        improvements=None,
        config=None,
    ):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.models = models
        self.skills = skills
        self.apprenticeship = apprenticeship
        self.actions = actions
        self.workflows = workflows
        self.capabilities = capabilities
        self.public_data = public_data
        self.services = services
        self.web_search = web_search
        self.improvements = improvements
        self.config = config or {}
        self.min_existing_score = float(self.config.get("acquisition_existing_score", 0.34))
        self.max_candidates = int(self.config.get("acquisition_max_candidates", 12))
        self._init_db()

    def _connect(self):
        c = sqlite3.connect(self.db_path, timeout=20)
        c.row_factory = sqlite3.Row
        return c

    def _now(self):
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def _init_db(self):
        with self._connect() as c:
            c.executescript(
                """
                CREATE TABLE IF NOT EXISTS gaps(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    goal TEXT NOT NULL,
                    normalized_goal TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'open',
                    reason TEXT DEFAULT '',
                    resolution_kind TEXT DEFAULT '',
                    resolution_id TEXT DEFAULT '',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_gaps_norm ON gaps(normalized_goal,status);

                CREATE TABLE IF NOT EXISTS candidates(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    gap_id INTEGER,
                    kind TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    source TEXT NOT NULL DEFAULT '',
                    risk TEXT NOT NULL DEFAULT 'read',
                    score REAL NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'proposed',
                    payload_json TEXT NOT NULL DEFAULT '{}',
                    test_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_candidates_gap ON candidates(gap_id,status);

                CREATE TABLE IF NOT EXISTS acquisition_events(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    gap_id INTEGER,
                    candidate_id INTEGER,
                    event TEXT NOT NULL,
                    detail_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                );
                """
            )

    # ------------------------------------------------------------------
    # Normalização / scoring
    # ------------------------------------------------------------------
    def _norm(self, value):
        s = unicodedata.normalize("NFKD", str(value or "").lower())
        s = "".join(ch for ch in s if not unicodedata.combining(ch))
        s = re.sub(r"[^a-z0-9_./:-]+", " ", s)
        return re.sub(r"\s+", " ", s).strip()

    def _tokens(self, value):
        stop = {
            "a","o","as","os","um","uma","de","da","do","das","dos","e","em","no","na",
            "nos","nas","para","por","com","sem","que","como","eu","voce","você","me","minha",
            "meu","quero","preciso","fazer","faca","faça","realizar","execute","executar","jarvis",
        }
        return {x for x in self._norm(value).replace("/", " ").replace("_", " ").split() if len(x) >= 3 and x not in stop}

    def _score(self, goal, label):
        q = self._norm(goal)
        h = self._norm(label)
        if not q or not h:
            return 0.0
        qt = self._tokens(q)
        ht = self._tokens(h)
        overlap = len(qt & ht) / max(1, len(qt))
        exact = 0.45 if q in h or h in q else 0.0
        return min(1.0, overlap * 0.65 + exact)

    def _decode_candidate(self, row):
        if not row:
            return None
        d = dict(row)
        for source, dest in (("payload_json", "payload"), ("test_json", "test")):
            try:
                d[dest] = json.loads(d.pop(source) or "{}")
            except Exception:
                d[dest] = {}
        return d

    # ------------------------------------------------------------------
    # Inventário do que já existe
    # ------------------------------------------------------------------
    def inventory(self, goal, limit=6):
        goal = str(goal or "").strip()
        data = {
            "skills": [], "actions": [], "workflows": [], "capabilities": [],
            "procedures": [], "services": [], "public_sources": [],
        }
        try:
            data["skills"] = self.skills.relevant_skills(goal, limit=limit)
        except Exception:
            pass
        try:
            data["actions"] = self.actions.search(goal, limit=limit).get("items", [])
        except Exception:
            pass
        try:
            data["workflows"] = self.workflows.search(goal, limit=limit).get("items", [])
        except Exception:
            pass
        try:
            data["capabilities"] = self.capabilities.search(goal, limit=limit).get("items", [])
        except Exception:
            pass
        try:
            data["procedures"] = self.apprenticeship.relevant(goal, limit=limit) if self.apprenticeship else []
        except Exception:
            pass
        try:
            data["services"] = self.services.context(goal, limit=limit).get("items", [])
        except Exception:
            pass
        try:
            data["public_sources"] = self.public_data.recommend(goal, limit=limit).get("items", [])
        except Exception:
            pass

        ranked = []
        for kind, items in data.items():
            for item in items:
                label = " ".join(str(item.get(k, "")) for k in (
                    "name", "id", "slug", "description", "title", "notes", "when_to_use", "group", "provider"
                ))
                score = self._score(goal, label)
                ranked.append({"kind": kind, "score": round(score, 3), "item": item})
        ranked.sort(key=lambda x: (-x["score"], x["kind"]))
        data["ranked"] = ranked[: max(8, limit * 2)]
        data["best"] = data["ranked"][0] if data["ranked"] else None
        return data

    def _existing_resolution(self, goal, inventory):
        executable_kinds = {"skills", "actions", "workflows", "capabilities", "services"}
        best = next((x for x in inventory.get("ranked", []) if x.get("kind") in executable_kinds), None)
        if not best or float(best.get("score", 0)) < self.min_existing_score:
            return None
        item = best.get("item") or {}
        kind = best.get("kind")
        identity = item.get("id") or item.get("slug") or item.get("name") or item.get("title")
        return {
            "ok": True,
            "status": "existing",
            "goal": goal,
            "kind": kind,
            "id": identity,
            "score": best.get("score"),
            "item": item,
            "message": f"Já existe uma competência relacionada em {kind}: {identity}.",
        }

    # ------------------------------------------------------------------
    # Gaps / candidatos
    # ------------------------------------------------------------------
    def _get_or_create_gap(self, goal, reason=""):
        norm = self._norm(goal)
        now = self._now()
        with self._connect() as c:
            row = c.execute(
                "SELECT * FROM gaps WHERE normalized_goal=? AND status IN ('open','discovering','awaiting_teaching') ORDER BY id DESC LIMIT 1",
                (norm,),
            ).fetchone()
            if row:
                c.execute(
                    "UPDATE gaps SET attempts=attempts+1,reason=?,updated_at=? WHERE id=?",
                    (str(reason or row["reason"] or ""), now, int(row["id"])),
                )
                return int(row["id"])
            cur = c.execute(
                "INSERT INTO gaps(goal,normalized_goal,status,reason,attempts,created_at,updated_at) VALUES(?,?,?,?,1,?,?)",
                (str(goal), norm, "open", str(reason or ""), now, now),
            )
            return int(cur.lastrowid)

    def _event(self, event, gap_id=None, candidate_id=None, **detail):
        with self._connect() as c:
            c.execute(
                "INSERT INTO acquisition_events(gap_id,candidate_id,event,detail_json,created_at) VALUES(?,?,?,?,?)",
                (gap_id, candidate_id, str(event), json.dumps(detail, ensure_ascii=False, default=str), self._now()),
            )

    def _add_candidate(self, gap_id, kind, title, description="", source="", risk="read", score=0.0, payload=None):
        now = self._now()
        payload = payload or {}
        payload_text = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
        with self._connect() as c:
            row = c.execute(
                "SELECT * FROM candidates WHERE gap_id=? AND kind=? AND title=? AND payload_json=? ORDER BY id DESC LIMIT 1",
                (int(gap_id), str(kind), str(title), payload_text),
            ).fetchone()
            if row:
                return self._decode_candidate(row)
            cur = c.execute(
                """INSERT INTO candidates(gap_id,kind,title,description,source,risk,score,status,payload_json,test_json,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,'proposed',?,'{}',?,?)""",
                (int(gap_id), str(kind), str(title), str(description), str(source), str(risk), float(score), payload_text, now, now),
            )
            cid = int(cur.lastrowid)
            row = c.execute("SELECT * FROM candidates WHERE id=?", (cid,)).fetchone()
        self._event("candidate_created", gap_id=gap_id, candidate_id=cid, kind=kind, title=title)
        return self._decode_candidate(row)

    def resolve(self, goal, create_gap=True):
        goal = str(goal or "").strip()
        if not goal:
            return {"ok": False, "error": "Objetivo vazio."}
        inv = self.inventory(goal)
        existing = self._existing_resolution(goal, inv)
        if existing:
            return {**existing, "inventory": inv}
        gap_id = self._get_or_create_gap(goal, "Nenhuma competência existente atingiu confiança suficiente.") if create_gap else None
        return {
            "ok": True,
            "status": "gap",
            "goal": goal,
            "gap_id": gap_id,
            "inventory": inv,
            "message": "Não encontrei uma competência executável com confiança suficiente.",
        }

    # ------------------------------------------------------------------
    # Recipe Factory
    # ------------------------------------------------------------------
    def _primitive_catalog(self, inventory):
        rows = []
        for kind in ("skills", "actions", "workflows", "capabilities", "services"):
            for item in inventory.get(kind, [])[:6]:
                identity = item.get("id") or item.get("slug") or item.get("name")
                if not identity:
                    continue
                rows.append({
                    "kind": kind[:-1] if kind.endswith("s") else kind,
                    "id": identity,
                    "description": item.get("description") or item.get("notes") or item.get("when_to_use") or item.get("name", ""),
                    "params": item.get("params") or item.get("inputs") or {},
                    "risk": item.get("risk", "read"),
                })
        return rows[:24]

    def _extract_json(self, text):
        raw = str(text or "").strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.I)
        raw = re.sub(r"\s*```$", "", raw)
        try:
            return json.loads(raw)
        except Exception:
            pass
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(raw[start:end+1])
            except Exception:
                return None
        return None

    def _lookup(self, kind, identity):
        if kind == "action":
            return self.actions.get(identity)
        if kind == "workflow":
            return self.workflows.get(identity)
        if kind == "capability":
            getter = getattr(self.capabilities, "get", None)
            if getter:
                return getter(identity)
            return getattr(self.capabilities, "_by_id", {}).get(str(identity))
        if kind == "skill":
            return self.skills.get_skill(identity)
        if kind == "service":
            try:
                r = self.services.resolve(identity)
                return r.get("data") if r.get("ok") else None
            except Exception:
                return None
        return None

    def _required_params(self, kind, meta):
        if not meta:
            return []
        specs = meta.get("params") if kind in {"action", "capability"} else meta.get("inputs")
        specs = specs or {}
        return [str(k) for k, spec in specs.items() if isinstance(spec, dict) and spec.get("required")]

    def _normalize_recipe(self, recipe):
        data = dict(recipe or {})
        data["name"] = str(data.get("name") or "Competência adquirida").strip()
        data["description"] = str(data.get("description") or "Receita adquirida pelo Capability Acquisition Engine.").strip()
        inputs = data.get("inputs") if isinstance(data.get("inputs"), dict) else {}
        steps = []
        seen_input_names = set(inputs)

        for index, raw in enumerate(data.get("steps") or [], 1):
            if not isinstance(raw, dict):
                continue
            kind = str(raw.get("kind") or raw.get("type") or "").lower().strip()
            identity = str(raw.get("id") or raw.get("target") or "").strip()
            if kind not in {"action", "workflow", "capability", "skill", "service"} or not identity:
                continue
            meta = self._lookup(kind, identity)
            if not meta:
                continue
            params = raw.get("params") if isinstance(raw.get("params"), dict) else {}
            params = dict(params)
            for required in self._required_params(kind, meta):
                if required in params and params.get(required) not in (None, ""):
                    continue
                name = required
                if name in seen_input_names:
                    name = f"step{index}_{required}"
                seen_input_names.add(name)
                inputs.setdefault(name, {"required": True, "description": f"Entrada necessária para {identity}: {required}"})
                params[required] = "{{" + name + "}}"
            steps.append({"kind": kind, "id": identity, "params": params})

        data["inputs"] = inputs
        data["steps"] = steps
        return data

    def validate_recipe(self, recipe):
        normalized = self._normalize_recipe(recipe)
        issues = []
        max_risk = "read"
        for i, step in enumerate(normalized.get("steps", []), 1):
            kind, identity = step.get("kind"), step.get("id")
            meta = self._lookup(kind, identity)
            if not meta:
                issues.append(f"Passo {i}: {kind} '{identity}' não existe no runtime.")
                continue
            risk = str(meta.get("risk", "read"))
            if RISK_ORDER.get(risk, 1) > RISK_ORDER.get(max_risk, 0):
                max_risk = risk
        if not normalized.get("steps"):
            issues.append("A receita não possui passos executáveis válidos.")
        return {
            "ok": not issues,
            "issues": issues,
            "recipe": normalized,
            "risk": max_risk,
            "steps": len(normalized.get("steps", [])),
            "inputs": normalized.get("inputs", {}),
        }

    def _synthesize_recipe(self, goal, inventory, status=None):
        primitives = self._primitive_catalog(inventory)
        if not primitives or not self.models:
            return None
        if status:
            status("Capability Factory: tentando compor uma nova Skill")
        prompt = (
            "Você é o Capability Factory do Jarvis. Crie uma receita DECLARATIVA para cumprir o objetivo usando SOMENTE os IDs listados. "
            "Não invente ferramentas. Não escreva código, shell ou PowerShell. Responda APENAS JSON com: "
            '{"name":"...","description":"...","inputs":{},"steps":[{"kind":"action|workflow|capability|skill|service","id":"ID_EXATO","params":{}}]}. '
            "Use poucos passos e deixe params desconhecidos vazios; o validador os transforma em inputs.\n\n"
            f"OBJETIVO:\n{goal}\n\nPRIMITIVAS DISPONÍVEIS:\n{json.dumps(primitives, ensure_ascii=False, indent=2)[:9000]}"
        )
        try:
            resp = self.models.chat(
                [
                    {"role": "system", "content": "Monte receitas executáveis apenas com primitivas fornecidas. Nunca exponha chain-of-thought."},
                    {"role": "user", "content": prompt},
                ],
                user_text=goal,
                force="reason",
            )
            parsed = self._extract_json((resp.get("message") or {}).get("content", ""))
            if not isinstance(parsed, dict):
                return None
            checked = self.validate_recipe(parsed)
            return checked if checked.get("ok") else None
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Descoberta pública / aquisição
    # ------------------------------------------------------------------
    def discover(self, goal, source_url=None, status=None):
        result = self.resolve(goal, create_gap=True)
        if result.get("status") == "existing":
            return result
        gap_id = result.get("gap_id")
        inventory = result.get("inventory") or self.inventory(goal)
        candidates = []

        with self._connect() as c:
            c.execute("UPDATE gaps SET status='discovering',updated_at=? WHERE id=?", (self._now(), int(gap_id)))

        # 1) Tentar compor uma nova Skill apenas com primitivas já confiáveis.
        recipe = self._synthesize_recipe(goal, inventory, status=status)
        if recipe and recipe.get("ok"):
            rec = recipe.get("recipe") or {}
            candidate = self._add_candidate(
                gap_id, "recipe", rec.get("name", "Skill composta"),
                description=rec.get("description", ""), source="runtime_primitives",
                risk=recipe.get("risk", "read"), score=0.92,
                payload={"recipe": rec, "validation": {"steps": recipe.get("steps"), "inputs": recipe.get("inputs", {})}},
            )
            candidates.append(candidate)

        # 2) Se o usuário forneceu uma URL pública, procurar interfaces padrão.
        if source_url:
            try:
                discovered = self.public_data.discover_interfaces(source_url, save=True)
            except Exception as exc:
                discovered = {"ok": False, "error": str(exc)}
            for item in discovered.get("interfaces", []) if discovered.get("ok") else []:
                kind = item.get("kind")
                if kind == "openapi":
                    candidates.append(self._add_candidate(
                        gap_id, "openapi_import", f"OpenAPI descoberta em {source_url}",
                        description="Importar endpoints GET públicos e anônimos como capacidades read-only.",
                        source=source_url, risk="read", score=0.86,
                        payload={"spec_url": item.get("url"), "prefix": self._norm(goal).replace(" ", "-")[:40] or "acquired"},
                    ))
                else:
                    candidates.append(self._add_candidate(
                        gap_id, "public_interface", f"Interface pública {kind}",
                        description=f"Interface {kind} encontrada durante a descoberta.",
                        source=source_url, risk="read", score=0.55,
                        payload=item,
                    ))

        # 3) Catálogo público de OpenAPI (APIs.guru), sem instalar automaticamente.
        try:
            api_results = self.capabilities.discover_public_apis(goal, limit=5)
        except Exception as exc:
            api_results = {"ok": False, "error": str(exc)}
        if api_results.get("ok"):
            for item in api_results.get("items", [])[:5]:
                candidates.append(self._add_candidate(
                    gap_id, "openapi_import", item.get("title") or item.get("api_id") or "API pública",
                    description=item.get("description", ""), source="apis.guru", risk="read",
                    score=0.68, payload={
                        "spec_url": item.get("spec_url"),
                        "prefix": self._norm(item.get("title") or item.get("api_id") or "acquired").replace(" ", "-")[:40],
                        "api_id": item.get("api_id"),
                    },
                ))

        # 4) Fontes públicas conhecidas podem resolver a parte de informação.
        for item in inventory.get("public_sources", [])[:4]:
            candidates.append(self._add_candidate(
                gap_id, "public_source", item.get("name") or item.get("id") or "Fonte pública",
                description=item.get("notes") or item.get("description") or "Fonte de dados já catalogada.",
                source=item.get("id") or "public_data", risk="read", score=0.5,
                payload={"source_id": item.get("id"), "access": item.get("access"), "operations": item.get("operations")},
            ))

        # 5) Documentação web é evidência para um próximo passo, não executor.
        if self.web_search and len(candidates) < 2:
            try:
                docs = self.web_search.search(f"{goal} API documentação oficial", limit=4)
            except Exception:
                docs = {"ok": False}
            for item in docs.get("items", [])[:3] if docs.get("ok") else []:
                candidates.append(self._add_candidate(
                    gap_id, "documentation", item.get("title") or "Documentação",
                    description=item.get("snippet", ""), source=item.get("url", ""), risk="read", score=0.35,
                    payload={"url": item.get("url"), "snippet": item.get("snippet", "")},
                ))

        # Deduplicate current return list by id.
        unique = []
        seen = set()
        for c in candidates:
            if not c or c.get("id") in seen:
                continue
            seen.add(c.get("id"))
            unique.append(c)
        unique.sort(key=lambda x: (-float(x.get("score", 0)), int(x.get("id", 0))))
        unique = unique[: self.max_candidates]

        if unique:
            with self._connect() as c:
                c.execute("UPDATE gaps SET status='open',updated_at=? WHERE id=?", (self._now(), int(gap_id)))
            self._event("discovery_complete", gap_id=gap_id, candidates=len(unique))
        else:
            with self._connect() as c:
                c.execute("UPDATE gaps SET status='awaiting_teaching',updated_at=? WHERE id=?", (self._now(), int(gap_id)))
            self._event("teaching_required", gap_id=gap_id)

        return {
            "ok": True,
            "status": "candidates" if unique else "awaiting_teaching",
            "goal": goal,
            "gap_id": gap_id,
            "candidates": unique,
            "teaching_available": True,
            "message": (
                f"Encontrei {len(unique)} caminho(s) candidato(s) para adquirir essa competência."
                if unique else
                "Não encontrei um executor confiável. O próximo caminho é você me ensinar por explicação ou demonstração."
            ),
        }

    def test_candidate(self, candidate_id):
        with self._connect() as c:
            row = c.execute("SELECT * FROM candidates WHERE id=?", (int(candidate_id),)).fetchone()
        candidate = self._decode_candidate(row)
        if not candidate:
            return {"ok": False, "error": "Candidato não encontrado."}

        kind = candidate.get("kind")
        payload = candidate.get("payload") or {}
        if kind == "recipe":
            check = self.validate_recipe((payload.get("recipe") or {}))
        elif kind == "openapi_import":
            url = str(payload.get("spec_url") or "")
            parsed = urlparse(url)
            check = {
                "ok": parsed.scheme == "https" and bool(parsed.netloc),
                "spec_url": url,
                "note": "A importação real ainda validará HTTPS público, GET anônimo e ausência de autenticação.",
            }
        elif kind in {"public_source", "public_interface", "documentation"}:
            check = {"ok": True, "note": "Candidato informacional; não executa ações externas."}
        else:
            check = {"ok": False, "error": f"Tipo de candidato não testável: {kind}"}

        status = "validated" if check.get("ok") else "failed"
        with self._connect() as c:
            c.execute(
                "UPDATE candidates SET status=?,test_json=?,updated_at=? WHERE id=?",
                (status, json.dumps(check, ensure_ascii=False, default=str), self._now(), int(candidate_id)),
            )
        self._event("candidate_tested", gap_id=candidate.get("gap_id"), candidate_id=int(candidate_id), ok=bool(check.get("ok")))
        return {"ok": bool(check.get("ok")), "candidate_id": int(candidate_id), "test": check, "status": status}

    def _recipe_to_skill_steps(self, recipe):
        steps = []
        for step in recipe.get("steps", []):
            kind = step.get("kind")
            identity = step.get("id")
            params = step.get("params") or {}
            if kind == "action":
                steps.append({"tool": "execute_action", "args": {"action_id": identity, "params": params}})
            elif kind == "workflow":
                steps.append({"tool": "execute_workflow", "args": {"workflow_id": identity, "params": params}})
            elif kind == "capability":
                steps.append({"tool": "execute_capability", "args": {"capability_id": identity, "params": params}})
            elif kind == "skill":
                steps.append({"tool": "run_skill", "args": {"name": identity, "inputs": params}})
            elif kind == "service":
                # Service recipe is useful mainly for opening/navigating known services.
                operation = params.pop("operation", "open") if isinstance(params, dict) else "open"
                steps.append({"tool": "institutional_service", "args": {"operation": operation, "query": identity}})
        return steps

    def install_candidate(self, candidate_id):
        with self._connect() as c:
            row = c.execute("SELECT * FROM candidates WHERE id=?", (int(candidate_id),)).fetchone()
        candidate = self._decode_candidate(row)
        if not candidate:
            return {"ok": False, "error": "Candidato não encontrado."}

        if candidate.get("status") not in {"validated", "proposed"}:
            return {"ok": False, "error": f"Candidato em estado '{candidate.get('status')}' não pode ser instalado."}

        test = self.test_candidate(candidate_id)
        if not test.get("ok"):
            return test

        kind = candidate.get("kind")
        payload = candidate.get("payload") or {}
        installed_id = ""
        result = None

        if kind == "recipe":
            recipe = self.validate_recipe(payload.get("recipe") or {}).get("recipe") or {}
            skill_steps = self._recipe_to_skill_steps(recipe)
            metadata = {
                "acquired_by": "CapabilityAcquisitionEngine",
                "candidate_id": int(candidate_id),
                "gap_id": candidate.get("gap_id"),
                "source": candidate.get("source"),
                "risk": candidate.get("risk"),
                "confidence": candidate.get("score"),
                "validated": True,
            }
            saver = getattr(self.skills, "save_recipe_skill", None)
            if saver:
                result = saver(
                    recipe.get("name") or candidate.get("title"), skill_steps,
                    inputs=recipe.get("inputs") or {},
                    description=recipe.get("description") or candidate.get("description", ""),
                    metadata=metadata,
                )
            else:
                result = self.skills.save_parametric_skill(
                    recipe.get("name") or candidate.get("title"), skill_steps,
                    inputs=recipe.get("inputs") or {},
                    description=recipe.get("description") or candidate.get("description", ""),
                )
            installed_id = (result or {}).get("name", "")

        elif kind == "openapi_import":
            result = self.capabilities.import_openapi(
                payload.get("spec_url", ""),
                prefix=payload.get("prefix") or "acquired",
                max_operations=int(self.config.get("acquisition_openapi_max_operations", 40)),
            )
            installed_id = str(result.get("title") or payload.get("prefix") or "openapi") if result else ""
        else:
            return {"ok": False, "error": f"O candidato '{kind}' é informacional e não instala um executor."}

        if not result or not result.get("ok"):
            with self._connect() as c:
                c.execute("UPDATE candidates SET status='failed',updated_at=? WHERE id=?", (self._now(), int(candidate_id)))
            self._event("install_failed", gap_id=candidate.get("gap_id"), candidate_id=int(candidate_id), result=result or {})
            return result or {"ok": False, "error": "Falha na instalação."}

        with self._connect() as c:
            c.execute("UPDATE candidates SET status='installed',updated_at=? WHERE id=?", (self._now(), int(candidate_id)))
            c.execute(
                "UPDATE gaps SET status='resolved',resolution_kind=?,resolution_id=?,updated_at=? WHERE id=?",
                (kind, installed_id, self._now(), int(candidate.get("gap_id"))),
            )
        self._event("installed", gap_id=candidate.get("gap_id"), candidate_id=int(candidate_id), installed_id=installed_id)
        return {
            "ok": True,
            "candidate_id": int(candidate_id),
            "installed_kind": kind,
            "installed_id": installed_id,
            "result": result,
        }

    # ------------------------------------------------------------------
    # Failure learning / status
    # ------------------------------------------------------------------
    def record_failure(self, goal, error):
        resolved = self.resolve(goal, create_gap=False)
        if resolved.get("status") == "existing":
            return {"ok": True, "recorded": False, "reason": "Já existe executor relacionado; falha pode ser operacional."}
        gap_id = self._get_or_create_gap(goal, str(error)[:1000])
        self._event("execution_failure", gap_id=gap_id, error=str(error)[:1200])
        if self.improvements:
            try:
                self.improvements.propose(
                    "capability_gap",
                    f"Lacuna de capacidade: {str(goal)[:90]}",
                    "Uma tarefa falhou sem executor confiável. Avaliar descoberta, integração ou ensino.",
                    evidence={"goal": goal, "error": str(error), "gap_id": gap_id},
                    priority=65,
                )
            except Exception:
                pass
        return {"ok": True, "recorded": True, "gap_id": gap_id}

    def list_gaps(self, status=None, limit=50):
        sql = "SELECT * FROM gaps"
        args = []
        if status:
            sql += " WHERE status=?"
            args.append(str(status))
        sql += " ORDER BY updated_at DESC LIMIT ?"
        args.append(int(limit))
        with self._connect() as c:
            rows = c.execute(sql, args).fetchall()
        return {"ok": True, "items": [dict(x) for x in rows], "count": len(rows)}

    def list_candidates(self, gap_id=None, status=None, limit=50):
        sql = "SELECT * FROM candidates WHERE 1=1"
        args = []
        if gap_id is not None:
            sql += " AND gap_id=?"
            args.append(int(gap_id))
        if status:
            sql += " AND status=?"
            args.append(str(status))
        sql += " ORDER BY score DESC,id DESC LIMIT ?"
        args.append(int(limit))
        with self._connect() as c:
            rows = c.execute(sql, args).fetchall()
        return {"ok": True, "items": [self._decode_candidate(x) for x in rows], "count": len(rows)}

    def context(self, query, max_chars=2200):
        norm = self._norm(query)
        with self._connect() as c:
            gaps = c.execute(
                "SELECT * FROM gaps WHERE status IN ('open','discovering','awaiting_teaching') ORDER BY updated_at DESC LIMIT 20"
            ).fetchall()
        scored = []
        for row in gaps:
            score = self._score(query, row["goal"])
            if score > 0.12 or self._norm(row["goal"]) in norm or norm in self._norm(row["goal"]):
                scored.append((score, dict(row)))
        scored.sort(key=lambda x: -x[0])
        if not scored:
            return {"ok": True, "text": "", "items": []}
        lines = []
        items = []
        for score, gap in scored[:3]:
            items.append(gap)
            candidates = self.list_candidates(gap_id=gap["id"], limit=3).get("items", [])
            lines.append(f"- Lacuna #{gap['id']} [{gap['status']}]: {gap['goal']}")
            for cand in candidates:
                lines.append(f"  • candidato #{cand['id']} {cand['kind']}: {cand['title']} [{cand['status']}]")
        return {
            "ok": True,
            "items": items,
            "text": ("CAPABILITY ACQUISITION — histórico relevante:\n" + "\n".join(lines))[:int(max_chars)],
        }

    def stats(self):
        with self._connect() as c:
            gaps = c.execute("SELECT status,COUNT(*) n FROM gaps GROUP BY status").fetchall()
            candidates = c.execute("SELECT status,COUNT(*) n FROM candidates GROUP BY status").fetchall()
        return {
            "ok": True,
            "gaps": {x["status"]: x["n"] for x in gaps},
            "candidates": {x["status"]: x["n"] for x in candidates},
        }
