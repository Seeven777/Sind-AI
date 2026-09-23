import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path


class WorkplaceIntelligence:
    """Deterministic, local-first broker for institutional playbooks."""

    def __init__(self, registry_path, db_path, services=None, long_horizon=None, config=None, user_registry_path=None, experience=None):
        self.registry_path = Path(registry_path)
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.config = dict(config or {})
        data = json.loads(self.registry_path.read_text(encoding="utf-8"))
        self.native_items = list(data.get("playbooks", []))
        self.categories = dict(data.get("categories", {}))
        self.user_registry_path = Path(user_registry_path) if user_registry_path else None
        if self.user_registry_path:
            self.user_registry_path.parent.mkdir(parents=True, exist_ok=True)
        self.services = services
        self.long_horizon = long_horizon
        self.experience = experience
        self.items = []
        self.by_id = {}
        self._reload_items()
        self._init_db()

    def _load_user_playbooks(self):
        if not self.user_registry_path or not self.user_registry_path.exists():
            return []
        try:
            data=json.loads(self.user_registry_path.read_text(encoding="utf-8"))
            return list(data.get("playbooks",[]))
        except Exception:
            return []

    def _reload_items(self):
        custom=self._load_user_playbooks()
        merged={x["id"]:dict(x) for x in self.native_items}
        for item in custom:
            if item.get("id"):
                merged[item["id"]]=dict(item)
                cat=item.get("category")
                if cat and cat not in self.categories:
                    self.categories[cat]=cat
        self.items=list(merged.values())
        self.by_id={x["id"]:x for x in self.items}
        return {"ok":True,"native":len(self.native_items),"custom":len(custom),"total":len(self.items)}

    def _save_user_playbooks(self,items):
        if not self.user_registry_path:
            return {"ok":False,"error":"Registro de playbooks aprendidos não configurado."}
        payload={"version":1,"playbooks":items}
        self.user_registry_path.write_text(
            json.dumps(payload,ensure_ascii=False,indent=2),
            encoding="utf-8"
        )
        self._reload_items()
        return {"ok":True,"path":str(self.user_registry_path),"count":len(items)}

    def install_custom(self,playbook):
        item=dict(playbook or {})
        required=("id","name","category","description","steps")
        missing=[x for x in required if not item.get(x)]
        if missing:
            return {"ok":False,"error":"Campos ausentes: "+", ".join(missing)}
        item["id"]=str(item["id"]).strip().lower()
        if not item["id"].startswith("custom."):
            item["id"]="custom."+re.sub(r"[^a-z0-9_.-]+","_",item["id"]).strip("_.")
        item["free_only"]=True
        item.setdefault("risk","read")
        item.setdefault("services",[])
        item.setdefault("agents",["planner","reviewer"])
        item.setdefault("keywords",[])
        item.setdefault("inputs",{})
        item.setdefault("expected_outputs",[])
        clean_steps=[]
        for step in item.get("steps",[]):
            if isinstance(step,str):
                clean_steps.append({"title":step[:160],"instruction":step,"retry_safe":True})
            else:
                s=dict(step)
                title=str(s.get("title") or "Etapa").strip()
                instruction=str(s.get("instruction") or title).strip()
                clean_steps.append({
                    "title":title[:160],
                    "instruction":instruction[:6000],
                    "retry_safe":bool(s.get("retry_safe",True)),
                })
        if not clean_steps:
            return {"ok":False,"error":"Playbook sem etapas válidas."}
        item["steps"]=clean_steps[:12]
        custom=self._load_user_playbooks()
        custom=[x for x in custom if x.get("id")!=item["id"]]
        custom.append(item)
        saved=self._save_user_playbooks(custom)
        if saved.get("ok"):
            return {"ok":True,"id":item["id"],"data":item,"custom_count":saved["count"]}
        return saved

    def create_from_job(self,job,name=None,category="learned"):
        if not job:
            return {"ok":False,"error":"Job não informado."}
        steps=[]
        for raw in job.get("steps",[]):
            title=str(raw.get("title") or f"Etapa {len(steps)+1}")
            instruction=str(raw.get("instruction") or title)
            steps.append({
                "title":title,
                "instruction":instruction,
                "retry_safe":bool(raw.get("retry_safe",True)),
            })
        if not steps:
            return {"ok":False,"error":"O job não possui etapas reutilizáveis."}
        base_name=str(name or job.get("goal") or "Rotina aprendida").strip()
        slug=re.sub(r"[^a-z0-9]+","_",base_name.lower()).strip("_")[:70] or "rotina"
        pid=f"custom.{slug}"
        if pid in self.by_id:
            suffix=2
            while f"{pid}_{suffix}" in self.by_id:
                suffix+=1
            pid=f"{pid}_{suffix}"
        metadata=dict(job.get("metadata") or {})
        playbook={
            "id":pid,
            "name":base_name[:160],
            "category":category,
            "description":f"Rotina aprendida a partir do Job #{job.get('id')}: {job.get('goal')}",
            "keywords":re.findall(r"[a-zà-ÿ0-9_-]{3,}",base_name.lower())[:10],
            "services":list(metadata.get("services") or []),
            "agents":list(metadata.get("agents") or ["planner","reviewer"]),
            "risk":"read" if all(x.get("retry_safe",True) for x in steps) else "write",
            "long_horizon":len(steps)>=4,
            "free_only":True,
            "inputs":{},
            "expected_outputs":["resultado reutilizável","registro de execução"],
            "steps":steps,
            "learned_from_job":job.get("id"),
        }
        return self.install_custom(playbook)

    def recent_usage(self,limit=30):
        with self._connect() as c:
            rows=c.execute(
                "SELECT * FROM workplace_usage ORDER BY id DESC LIMIT ?",
                (int(limit),)
            ).fetchall()
        return {"ok":True,"items":[dict(x) for x in rows],"count":len(rows)}

    def _connect(self):
        c = sqlite3.connect(self.db_path, timeout=20)
        c.row_factory = sqlite3.Row
        return c

    def _now(self):
        return datetime.now().isoformat(timespec="seconds")

    def _init_db(self):
        with self._connect() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS workplace_usage(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              playbook_id TEXT NOT NULL,
              query TEXT,
              status TEXT NOT NULL DEFAULT 'started',
              result_note TEXT,
              job_id INTEGER,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_workplace_usage_playbook
            ON workplace_usage(playbook_id,status,id);
            """)

    def set_adapters(self, services=None, long_horizon=None, experience=None):
        if services is not None:
            self.services = services
        if long_horizon is not None:
            self.long_horizon = long_horizon
        if experience is not None:
            self.experience = experience
        return {"ok": True}

    def stats(self):
        with self._connect() as c:
            rows = c.execute(
                "SELECT status,COUNT(*) n FROM workplace_usage GROUP BY status"
            ).fetchall()
        usage = {x["status"]: int(x["n"]) for x in rows}
        custom_count=max(0,len(self.items)-len(self.native_items))
        return {
            "ok": True,
            "playbooks": len(self.items),
            "native_playbooks": len(self.native_items),
            "custom_playbooks": custom_count,
            "categories": len(self.categories),
            "free_only": sum(1 for x in self.items if x.get("free_only", True)),
            "long_horizon": sum(1 for x in self.items if x.get("long_horizon")),
            "usage": usage,
        }

    def list(self, category=None, risk=None, service=None, limit=200):
        items = list(self.items)
        if category:
            items = [x for x in items if x.get("category") == str(category)]
        if risk:
            items = [x for x in items if x.get("risk") == str(risk)]
        if service:
            items = [x for x in items if str(service) in x.get("services", [])]
        items = items[: max(1, int(limit))]
        return {"ok": True, "items": items, "count": len(items)}

    def get(self, playbook_id):
        item = self.by_id.get(str(playbook_id))
        if not item:
            return {"ok": False, "error": f"Playbook não encontrado: {playbook_id}"}
        return {"ok": True, "data": item}

    def _tokens(self, text):
        return re.findall(r"[a-zà-ÿ0-9_-]{2,}", str(text or "").lower())

    def _usage_bonus(self):
        bonus = {}
        with self._connect() as c:
            rows = c.execute(
                """SELECT playbook_id,
                          SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) completed,
                          COUNT(*) total
                   FROM workplace_usage GROUP BY playbook_id"""
            ).fetchall()
        for row in rows:
            total = int(row["total"] or 0)
            completed = int(row["completed"] or 0)
            if total:
                bonus[row["playbook_id"]] = min(4.0, (completed / total) * 2 + min(total, 10) * 0.12)
        return bonus

    def search(self, query, limit=12, category=None):
        q = str(query or "").strip().lower()
        if not q:
            return self.list(category=category, limit=limit)
        q_tokens = self._tokens(q)
        usage_bonus = self._usage_bonus()
        ranked = []
        for item in self.items:
            if category and item.get("category") != category:
                continue
            name = str(item.get("name", "")).lower()
            desc = str(item.get("description", "")).lower()
            keys = " ".join(item.get("keywords", [])).lower()
            services = " ".join(item.get("services", [])).lower()
            agents = " ".join(item.get("agents", [])).lower()
            hay = " ".join([item.get("id", "").lower(), name, desc, keys, services, agents])
            score = 0.0
            if q == item.get("id", "").lower():
                score += 100
            if q == name:
                score += 60
            if q in name:
                score += 24
            if q in keys:
                score += 18
            if q in desc:
                score += 8
            matched = 0
            for tok in q_tokens:
                if tok in name:
                    score += 5
                    matched += 1
                elif tok in keys:
                    score += 4
                    matched += 1
                elif tok in desc:
                    score += 2
                    matched += 1
                elif tok in hay:
                    score += 1
                    matched += 1
            if q_tokens and matched == len(q_tokens):
                score += 4
            score += usage_bonus.get(item["id"], 0)
            if self.experience:
                try:
                    score += float(self.experience.ranking_bonus(item["id"]))
                except Exception:
                    pass
            if score > 0:
                ranked.append((score, item))
        ranked.sort(key=lambda x: (-x[0], x[1]["name"]))
        out = []
        for score, item in ranked[: max(1, int(limit))]:
            row = dict(item)
            row["score"] = round(score, 2)
            out.append(row)
        return {"ok": True, "items": out, "count": len(out), "query": query}

    def recommend(self, query, limit=5):
        return self.search(query, limit=limit)

    def context(self, query, limit=None, max_chars=4200):
        if not self.config.get("workplace_auto_context", True):
            return {"ok": True, "text": "", "items": []}
        if limit is None:
            limit = int(self.config.get("workplace_max_context_playbooks", 3))
        found = self.search(query, limit=limit).get("items", [])
        if not found:
            return {"ok": True, "text": "", "items": []}
        chunks = ["PLAYBOOKS OPERACIONAIS RELEVANTES"]
        for item in found:
            steps = item.get("steps", [])
            step_text = "; ".join(str(x.get("title")) for x in steps[:5])
            chunks.append(
                f"- {item['name']} [{item['id']}]: {item['description']} "
                f"Serviços preferidos: {', '.join(item.get('services', [])) or 'nenhum'}. "
                f"Fluxo: {step_text}."
            )
        text = "\n".join(chunks)[: int(max_chars)]
        return {"ok": True, "text": text, "items": found}

    def open_services(self, playbook_id):
        got = self.get(playbook_id)
        if not got.get("ok"):
            return got
        item = got["data"]
        results = []
        if self.services:
            cap = max(0, int(self.config.get("workplace_preopen_services", 2)))
            service_ids = list(item.get("services", []))[:cap] if cap else []
            for sid in service_ids:
                try:
                    results.append(self.services.open(sid))
                except Exception as exc:
                    results.append({"ok": False, "service": sid, "error": str(exc)})
        return {"ok": True, "playbook_id": playbook_id, "items": results}

    def compile_prompt(self, playbook_id, request=""):
        got = self.get(playbook_id)
        if not got.get("ok"):
            return got
        item = got["data"]
        steps = "\n".join(
            f"{i+1}. {x.get('title')}: {x.get('instruction')}"
            for i, x in enumerate(item.get("steps", []))
        )
        experience_guidance=""
        if self.experience:
            try:
                experience_guidance=self.experience.guidance(item["id"]).get("text","")
            except Exception:
                experience_guidance=""

        prompt = f"""[WORKPLACE PLAYBOOK]
PLAYBOOK: {item['name']}
ID: {item['id']}
CATEGORIA: {item.get('category')}
OBJETIVO: {item.get('description')}
PEDIDO ORIGINAL: {request or item.get('description')}
SERVIÇOS PREFERIDOS: {', '.join(item.get('services', [])) or 'nenhum'}
AGENTES RECOMENDADOS: {', '.join(item.get('agents', [])) or 'nenhum'}
RISCO: {item.get('risk','read')}

FLUXO RECOMENDADO:
{steps}

{experience_guidance}

Regras:
- Use as abas institucionais persistentes antes de pesquisa genérica quando elas contiverem a informação necessária.
- Use apenas ferramentas e fontes gratuitas/local-first, salvo autorização explícita em outra camada.
- Diferencie fatos confirmados, inferências e lacunas.
- Não exponha raciocínio interno.
- Operações externas sensíveis continuam sujeitas à confirmação.
""".strip()
        return {"ok": True, "prompt": prompt, "data": item}

    def _record_start(self, playbook_id, query, job_id=None):
        now = self._now()
        with self._connect() as c:
            cur = c.execute(
                """INSERT INTO workplace_usage(playbook_id,query,status,job_id,created_at,updated_at)
                   VALUES(?,?,?,?,?,?)""",
                (str(playbook_id), str(query or ""), "started", job_id, now, now),
            )
            return int(cur.lastrowid)

    def record_outcome(self, usage_id=None, playbook_id=None, status="completed", note=""):
        with self._connect() as c:
            if usage_id:
                cur = c.execute(
                    "UPDATE workplace_usage SET status=?,result_note=?,updated_at=? WHERE id=?",
                    (str(status), str(note)[:5000], self._now(), int(usage_id)),
                )
            elif playbook_id:
                row = c.execute(
                    "SELECT id FROM workplace_usage WHERE playbook_id=? ORDER BY id DESC LIMIT 1",
                    (str(playbook_id),),
                ).fetchone()
                if not row:
                    return {"ok": False, "error": "Uso do playbook não encontrado."}
                cur = c.execute(
                    "UPDATE workplace_usage SET status=?,result_note=?,updated_at=? WHERE id=?",
                    (str(status), str(note)[:5000], self._now(), int(row["id"])),
                )
            else:
                return {"ok": False, "error": "Informe usage_id ou playbook_id."}
        return {"ok": cur.rowcount > 0, "status": status}

    def start_long_horizon(self, playbook_id, request="", project_id=None, session_id=None, priority=60):
        got = self.get(playbook_id)
        if not got.get("ok"):
            return got
        if not self.long_horizon:
            return {"ok": False, "error": "Long-Horizon Runtime indisponível."}
        item = got["data"]
        self.open_services(playbook_id)
        plan = [
            {
                "title": x.get("title"),
                "instruction": x.get("instruction"),
                "retry_safe": bool(x.get("retry_safe", True)),
            }
            for x in item.get("steps", [])
        ]
        goal = request.strip() if str(request or "").strip() else item.get("description")
        guidance=""
        if self.experience:
            try:
                guidance=self.experience.guidance(
                    item["id"], project_id=project_id, max_chars=3200
                ).get("text","")
            except Exception:
                guidance=""
        result = self.long_horizon.create(
            goal,
            plan=plan,
            project_id=project_id,
            session_id=session_id,
            auto_resume=True,
            priority=int(priority),
            metadata={
                "source": "workplace_playbook",
                "playbook_id": item["id"],
                "playbook_name": item["name"],
                "services": item.get("services", []),
                "agents": item.get("agents", []),
                "experience_guidance": guidance,
            },
        )
        job_id = (result.get("data") or {}).get("id") if result.get("ok") else None
        usage_id = self._record_start(item["id"], goal, job_id=job_id)
        if result.get("ok"):
            result["playbook"] = item
            result["usage_id"] = usage_id
        return result

    def suggestions(self, context_text, limit=6):
        found = self.search(context_text, limit=max(limit * 2, 12)).get("items", [])
        seen_categories = set()
        selected = []
        for item in found:
            cat = item.get("category")
            if cat not in seen_categories or len(selected) < 2:
                selected.append(item)
                seen_categories.add(cat)
            if len(selected) >= int(limit):
                break
        return {"ok": True, "items": selected, "count": len(selected)}
