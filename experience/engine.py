import json
import re
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path


POSITIVE_MARKERS = (
    "funcionou", "deu certo", "perfeito", "ótimo", "otimo", "excelente",
    "ficou bom", "gostei", "era isso", "isso mesmo", "boa", "resolvido",
)
NEGATIVE_MARKERS = (
    "não funcionou", "nao funcionou", "deu errado", "não deu certo", "nao deu certo",
    "ficou ruim", "não gostei", "nao gostei", "não era isso", "nao era isso",
    "está errado", "esta errado", "falhou", "erro",
)
CORRECTION_MARKERS = (
    "da próxima vez", "da proxima vez", "prefiro", "quero que", "evite",
    "não faça", "nao faca", "sempre", "nunca", "use ", "utilize ",
)


class AdaptiveExperienceEngine:
    """
    Camada de experiência do Jarvis.

    Não altera pesos do modelo. Aprende por:
    - eventos de sucesso/falha;
    - correções explícitas;
    - regras de playbook persistentes;
    - candidatos de adaptação;
    - criação supervisionada de rotinas reutilizáveis.
    """

    def __init__(self, db_path, workplace=None, long_horizon=None, config=None):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.workplace = workplace
        self.long_horizon = long_horizon
        self.config = dict(config or {})
        self.auto_soft_rules = bool(self.config.get("experience_auto_soft_rules", True))
        self.failure_threshold = max(1, int(self.config.get("experience_candidate_failure_threshold", 2)))
        self._init_db()

    def _connect(self):
        c = sqlite3.connect(self.db_path, timeout=20)
        c.row_factory = sqlite3.Row
        return c

    def _now(self):
        return datetime.now().isoformat(timespec="seconds")

    def _init_db(self):
        with self._connect() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS experience_events(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              created_at TEXT NOT NULL,
              event_type TEXT NOT NULL,
              source_type TEXT NOT NULL DEFAULT 'conversation',
              source_id TEXT,
              playbook_id TEXT,
              category TEXT,
              project_id INTEGER,
              query TEXT,
              note TEXT,
              score REAL NOT NULL DEFAULT 0,
              metadata_json TEXT NOT NULL DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS competence_profiles(
              competence_key TEXT PRIMARY KEY,
              kind TEXT NOT NULL,
              label TEXT NOT NULL,
              uses INTEGER NOT NULL DEFAULT 0,
              successes INTEGER NOT NULL DEFAULT 0,
              failures INTEGER NOT NULL DEFAULT 0,
              corrections INTEGER NOT NULL DEFAULT 0,
              confidence REAL NOT NULL DEFAULT .50,
              success_streak INTEGER NOT NULL DEFAULT 0,
              failure_streak INTEGER NOT NULL DEFAULT 0,
              last_seen TEXT,
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS playbook_rules(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              playbook_id TEXT NOT NULL,
              scope TEXT NOT NULL DEFAULT 'personal',
              project_id INTEGER,
              rule_text TEXT NOT NULL,
              source_event_id INTEGER,
              confidence REAL NOT NULL DEFAULT .90,
              active INTEGER NOT NULL DEFAULT 1,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS adaptation_candidates(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              target_type TEXT NOT NULL DEFAULT 'playbook',
              target_id TEXT NOT NULL,
              title TEXT NOT NULL,
              reason TEXT NOT NULL,
              patch_json TEXT NOT NULL DEFAULT '{}',
              confidence REAL NOT NULL DEFAULT .70,
              status TEXT NOT NULL DEFAULT 'proposed',
              source_event_id INTEGER,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              resolution_note TEXT
            );

            CREATE TABLE IF NOT EXISTS playbook_evolution(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              base_playbook_id TEXT NOT NULL,
              evolved_playbook_id TEXT,
              version INTEGER NOT NULL DEFAULT 1,
              source_job_id INTEGER,
              source_candidate_id INTEGER,
              change_note TEXT,
              created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_exp_events_playbook ON experience_events(playbook_id,id);
            CREATE INDEX IF NOT EXISTS idx_exp_events_type ON experience_events(event_type,id);
            CREATE INDEX IF NOT EXISTS idx_exp_rules_playbook ON playbook_rules(playbook_id,active,id);
            CREATE INDEX IF NOT EXISTS idx_exp_candidates_status ON adaptation_candidates(status,id);
            """)

    def set_adapters(self, workplace=None, long_horizon=None):
        if workplace is not None:
            self.workplace = workplace
        if long_horizon is not None:
            self.long_horizon = long_horizon
        return {"ok": True}

    def _decode(self, row):
        if not row:
            return None
        d = dict(row)
        if "metadata_json" in d:
            try:
                d["metadata"] = json.loads(d.pop("metadata_json") or "{}")
            except Exception:
                d["metadata"] = {}
        if "patch_json" in d:
            try:
                d["patch"] = json.loads(d.pop("patch_json") or "{}")
            except Exception:
                d["patch"] = {}
        if "active" in d:
            d["active"] = bool(d["active"])
        return d

    def _profile_key(self, kind, value):
        return f"{kind}:{str(value or '').strip().lower()}"

    def _update_profile(self, kind, value, label=None, outcome="neutral"):
        if not value:
            return None
        key = self._profile_key(kind, value)
        now = self._now()
        with self._connect() as c:
            row = c.execute(
                "SELECT * FROM competence_profiles WHERE competence_key=?",
                (key,)
            ).fetchone()
            if row:
                d = dict(row)
                uses = int(d["uses"]) + 1
                successes = int(d["successes"])
                failures = int(d["failures"])
                corrections = int(d["corrections"])
                success_streak = int(d["success_streak"])
                failure_streak = int(d["failure_streak"])
                if outcome == "success":
                    successes += 1
                    success_streak += 1
                    failure_streak = 0
                elif outcome == "failure":
                    failures += 1
                    failure_streak += 1
                    success_streak = 0
                elif outcome == "correction":
                    corrections += 1
                    failure_streak += 1
                    success_streak = 0
                # Bayesian-ish local confidence, penalizing repeated corrections.
                positive = successes + 1.5
                negative = failures + corrections * 0.7 + 1.5
                confidence = max(.12, min(.98, positive / (positive + negative)))
                c.execute(
                    """UPDATE competence_profiles
                       SET uses=?,successes=?,failures=?,corrections=?,confidence=?,
                           success_streak=?,failure_streak=?,last_seen=?,updated_at=?
                       WHERE competence_key=?""",
                    (uses,successes,failures,corrections,confidence,
                     success_streak,failure_streak,now,now,key)
                )
            else:
                successes = 1 if outcome == "success" else 0
                failures = 1 if outcome == "failure" else 0
                corrections = 1 if outcome == "correction" else 0
                confidence = .62 if outcome == "success" else .35 if outcome in {"failure","correction"} else .50
                c.execute(
                    """INSERT INTO competence_profiles(
                       competence_key,kind,label,uses,successes,failures,corrections,
                       confidence,success_streak,failure_streak,last_seen,updated_at
                       ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (key,kind,str(label or value),1,successes,failures,corrections,
                     confidence,1 if outcome=="success" else 0,
                     1 if outcome in {"failure","correction"} else 0,
                     now,now)
                )
        return key

    def record_event(self, event_type, source_type="conversation", source_id=None,
                     playbook_id=None, category=None, project_id=None, query="",
                     note="", score=0, metadata=None):
        now = self._now()
        with self._connect() as c:
            cur = c.execute(
                """INSERT INTO experience_events(
                   created_at,event_type,source_type,source_id,playbook_id,category,
                   project_id,query,note,score,metadata_json
                   ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (now,str(event_type),str(source_type),str(source_id) if source_id is not None else None,
                 str(playbook_id) if playbook_id else None,str(category) if category else None,
                 int(project_id) if project_id else None,str(query or "")[:6000],
                 str(note or "")[:8000],float(score),
                 json.dumps(metadata or {},ensure_ascii=False,default=str))
            )
            eid = int(cur.lastrowid)

        outcome = (
            "success" if event_type in {"success","positive_feedback","completed"} or score > .2
            else "failure" if event_type in {"failure","negative_feedback","failed"} or score < -.2
            else "correction" if event_type in {"correction","preference"} else "neutral"
        )
        if playbook_id:
            self._update_profile("playbook", playbook_id, playbook_id, outcome)
        if category:
            self._update_profile("category", category, category, outcome)
        return {"ok": True, "id": eid, "event_type": event_type}

    def recent_events(self, limit=30, event_type=None):
        sql = "SELECT * FROM experience_events"
        args = []
        if event_type:
            sql += " WHERE event_type=?"
            args.append(str(event_type))
        sql += " ORDER BY id DESC LIMIT ?"
        args.append(int(limit))
        with self._connect() as c:
            rows = c.execute(sql,args).fetchall()
        items = [self._decode(x) for x in rows]
        return {"ok": True, "items": items, "count": len(items)}

    def competence_map(self, kind=None, limit=100):
        sql = "SELECT * FROM competence_profiles"
        args = []
        if kind:
            sql += " WHERE kind=?"
            args.append(str(kind))
        sql += " ORDER BY confidence DESC,uses DESC,updated_at DESC LIMIT ?"
        args.append(int(limit))
        with self._connect() as c:
            rows = c.execute(sql,args).fetchall()
        items = [dict(x) for x in rows]
        return {"ok": True, "items": items, "count": len(items)}

    def record_agent_outcome(self,agent_id,success=True,source_id=None,note=""):
        outcome="success" if success else "failure"
        key=self._update_profile("agent",agent_id,agent_id,outcome)
        event=self.record_event(
            outcome,
            source_type="swarm_agent",
            source_id=source_id,
            query=str(agent_id),
            note=note,
            score=1 if success else -1,
            metadata={"agent_id":agent_id},
        )
        return {"ok":True,"competence_key":key,"event":event}

    def agent_bonus(self,agent_id):
        key=self._profile_key("agent",agent_id)
        with self._connect() as c:
            row=c.execute(
                "SELECT uses,confidence,success_streak,failure_streak FROM competence_profiles WHERE competence_key=?",
                (key,)
            ).fetchone()
        if not row:
            return 0.0
        return max(-2.0,min(2.0,
            (float(row["confidence"])-.5)*3
            + min(3,int(row["success_streak"]))*.25
            - min(3,int(row["failure_streak"]))*.35
        ))

    def ranking_bonus(self, playbook_id):
        key = self._profile_key("playbook", playbook_id)
        with self._connect() as c:
            row = c.execute(
                "SELECT uses,confidence,success_streak,failure_streak FROM competence_profiles WHERE competence_key=?",
                (key,)
            ).fetchone()
        if not row:
            return 0.0
        uses = int(row["uses"])
        confidence = float(row["confidence"])
        success_streak = int(row["success_streak"])
        failure_streak = int(row["failure_streak"])
        return max(-4.0, min(5.0, (confidence-.5)*6 + min(3,success_streak)*.5 - min(3,failure_streak)*.8 + min(uses,10)*.05))

    def add_rule(self, playbook_id, rule_text, scope="personal", project_id=None,
                 source_event_id=None, confidence=.92, active=True):
        rule = re.sub(r"\s+"," ",str(rule_text or "")).strip()
        if not playbook_id or len(rule) < 4:
            return {"ok": False, "error": "Playbook e regra são obrigatórios."}
        now = self._now()
        with self._connect() as c:
            row = c.execute(
                """SELECT id FROM playbook_rules
                   WHERE playbook_id=? AND lower(rule_text)=lower(?) AND active=1""",
                (str(playbook_id),rule)
            ).fetchone()
            if row:
                return {"ok": True, "id": int(row["id"]), "duplicate": True}
            cur = c.execute(
                """INSERT INTO playbook_rules(
                   playbook_id,scope,project_id,rule_text,source_event_id,confidence,active,created_at,updated_at
                   ) VALUES(?,?,?,?,?,?,?,?,?)""",
                (str(playbook_id),str(scope),int(project_id) if project_id else None,
                 rule,int(source_event_id) if source_event_id else None,float(confidence),
                 1 if active else 0,now,now)
            )
            rid = int(cur.lastrowid)
        return {"ok": True, "id": rid, "playbook_id": playbook_id, "rule": rule}

    def rules(self, playbook_id=None, project_id=None, active=True, limit=100):
        sql = "SELECT * FROM playbook_rules WHERE 1=1"
        args=[]
        if playbook_id:
            sql += " AND playbook_id=?"
            args.append(str(playbook_id))
        if active is not None:
            sql += " AND active=?"
            args.append(1 if active else 0)
        if project_id:
            sql += " AND (project_id IS NULL OR project_id=?)"
            args.append(int(project_id))
        else:
            sql += " AND project_id IS NULL"
        sql += " ORDER BY confidence DESC,id DESC LIMIT ?"
        args.append(int(limit))
        with self._connect() as c:
            rows=c.execute(sql,args).fetchall()
        return {"ok":True,"items":[self._decode(x) for x in rows],"count":len(rows)}

    def guidance(self, playbook_id, project_id=None, limit=None, max_chars=2600):
        if limit is None:
            limit=int(self.config.get("experience_max_context_rules",6))
        rows=self.rules(playbook_id,project_id=project_id,active=True,limit=limit).get("items",[])
        profile=None
        key=self._profile_key("playbook",playbook_id)
        with self._connect() as c:
            row=c.execute("SELECT * FROM competence_profiles WHERE competence_key=?",(key,)).fetchone()
            profile=dict(row) if row else None
        if not rows and not profile:
            return {"ok":True,"text":"","items":[]}

        chunks=["APRENDIZADOS ESPECÍFICOS DESTA ROTINA"]
        if profile:
            pct=round(float(profile.get("confidence",.5))*100)
            chunks.append(
                f"- Confiança observada: {pct}% após {profile.get('uses',0)} uso(s); "
                f"{profile.get('successes',0)} sucesso(s), {profile.get('failures',0)} falha(s), "
                f"{profile.get('corrections',0)} correção(ões)."
            )
            if int(profile.get("uses",0))>=2 and float(profile.get("confidence",.5))<.40:
                chunks.append(
                    "- Atenção: esta rotina teve desempenho baixo. Valide premissas e evidências antes de repetir o mesmo caminho."
                )
        chunks.extend(f"- {x['rule_text']}" for x in rows)
        return {"ok":True,"text":"\n".join(chunks)[:int(max_chars)],"items":rows,"profile":profile}

    def deactivate_rule(self,rule_id,note=""):
        with self._connect() as c:
            cur=c.execute(
                "UPDATE playbook_rules SET active=0,updated_at=? WHERE id=? AND active=1",
                (self._now(),int(rule_id))
            )
        if cur.rowcount:
            self.record_event(
                "rule_rollback",
                source_type="experience_control",
                source_id=rule_id,
                note=note or f"Regra #{rule_id} desativada.",
                score=0,
            )
        return {"ok":cur.rowcount>0,"rule_id":int(rule_id),"active":False}

    def rollback_last_rule(self,playbook_id=None):
        sql="SELECT * FROM playbook_rules WHERE active=1"
        args=[]
        if playbook_id:
            sql+=" AND playbook_id=?";args.append(str(playbook_id))
        sql+=" ORDER BY id DESC LIMIT 1"
        with self._connect() as c:
            row=c.execute(sql,args).fetchone()
        if not row:
            return {"ok":False,"error":"Nenhuma regra adaptativa ativa encontrada."}
        result=self.deactivate_rule(int(row["id"]),note="Rollback solicitado pelo usuário.")
        result["playbook_id"]=row["playbook_id"]
        result["rule_text"]=row["rule_text"]
        return result

    def _candidate_exists(self, target_id, reason):
        with self._connect() as c:
            row=c.execute(
                """SELECT id FROM adaptation_candidates
                   WHERE target_id=? AND lower(reason)=lower(?) AND status IN ('proposed','approved','installed')""",
                (str(target_id),str(reason))
            ).fetchone()
        return int(row["id"]) if row else None

    def propose_adaptation(self, playbook_id, reason, rule_text=None, source_event_id=None,
                           confidence=.74, auto_approve_soft=False):
        reason = re.sub(r"\s+"," ",str(reason or "")).strip()
        if not playbook_id or not reason:
            return {"ok":False,"error":"Playbook e motivo são obrigatórios."}
        existing=self._candidate_exists(playbook_id,reason)
        if existing:
            return {"ok":True,"id":existing,"duplicate":True}
        patch={
            "type":"guidance",
            "append_rules":[str(rule_text or reason).strip()],
        }
        status="approved" if auto_approve_soft else "proposed"
        now=self._now()
        with self._connect() as c:
            cur=c.execute(
                """INSERT INTO adaptation_candidates(
                   target_type,target_id,title,reason,patch_json,confidence,status,source_event_id,created_at,updated_at
                   ) VALUES('playbook',?,?,?,?,?,?,?,?,?)""",
                (str(playbook_id),f"Aprimorar {playbook_id}",reason,
                 json.dumps(patch,ensure_ascii=False),float(confidence),status,
                 int(source_event_id) if source_event_id else None,now,now)
            )
            cid=int(cur.lastrowid)
        if status=="approved":
            self.install_candidate(cid)
        return {"ok":True,"id":cid,"status":status,"target_id":playbook_id}

    def candidates(self, status="proposed", limit=100):
        sql="SELECT * FROM adaptation_candidates"
        args=[]
        if status:
            sql+=" WHERE status=?";args.append(str(status))
        sql+=" ORDER BY confidence DESC,id DESC LIMIT ?";args.append(int(limit))
        with self._connect() as c:
            rows=c.execute(sql,args).fetchall()
        return {"ok":True,"items":[self._decode(x) for x in rows],"count":len(rows)}

    def candidate(self, candidate_id):
        with self._connect() as c:
            row=c.execute("SELECT * FROM adaptation_candidates WHERE id=?",(int(candidate_id),)).fetchone()
        if not row:
            return {"ok":False,"error":"Adaptação não encontrada."}
        return {"ok":True,"data":self._decode(row)}

    def install_candidate(self, candidate_id):
        got=self.candidate(candidate_id)
        if not got.get("ok"):
            return got
        item=got["data"]
        patch=item.get("patch") or {}
        if item.get("target_type")!="playbook":
            return {"ok":False,"error":"Tipo de adaptação não suportado."}
        rules=[x for x in patch.get("append_rules",[]) if str(x).strip()]
        installed=[]
        for rule in rules:
            installed.append(self.add_rule(
                item["target_id"], rule,
                source_event_id=item.get("source_event_id"),
                confidence=max(.75,float(item.get("confidence") or .75))
            ))
        with self._connect() as c:
            c.execute(
                "UPDATE adaptation_candidates SET status='installed',updated_at=? WHERE id=?",
                (self._now(),int(candidate_id))
            )
        return {"ok":True,"candidate_id":int(candidate_id),"installed_rules":installed}

    def approve_candidate(self,candidate_id,note=""):
        with self._connect() as c:
            cur=c.execute(
                "UPDATE adaptation_candidates SET status='approved',resolution_note=?,updated_at=? WHERE id=? AND status='proposed'",
                (str(note)[:2000],self._now(),int(candidate_id))
            )
        if cur.rowcount<=0:
            got=self.candidate(candidate_id)
            if not got.get("ok"):
                return got
            if got["data"]["status"]=="installed":
                return {"ok":True,"candidate_id":int(candidate_id),"status":"installed"}
        return self.install_candidate(candidate_id)

    def reject_candidate(self,candidate_id,note=""):
        with self._connect() as c:
            cur=c.execute(
                "UPDATE adaptation_candidates SET status='rejected',resolution_note=?,updated_at=? WHERE id=? AND status IN ('proposed','approved')",
                (str(note)[:2000],self._now(),int(candidate_id))
            )
        return {"ok":cur.rowcount>0,"candidate_id":int(candidate_id),"status":"rejected"}

    def _resolve_recent_playbook(self):
        if not self.workplace:
            return None
        try:
            recent=self.workplace.recent_usage(limit=10).get("items",[])
            max_hours=max(1,float(self.config.get("experience_feedback_playbook_window_hours",6)))
            cutoff=datetime.now()-timedelta(hours=max_hours)
            for item in recent:
                if not item.get("playbook_id"):
                    continue
                raw=item.get("updated_at") or item.get("created_at")
                try:
                    when=datetime.fromisoformat(str(raw))
                except Exception:
                    when=None
                if when is not None and when < cutoff:
                    continue
                return item
        except Exception:
            pass
        return None

    def parse_feedback(self,text):
        raw=re.sub(r"\s+"," ",str(text or "")).strip()
        low=raw.lower()
        if any(x in low for x in NEGATIVE_MARKERS):
            kind="negative_feedback";score=-1.0
        elif any(x in low for x in POSITIVE_MARKERS):
            kind="positive_feedback";score=1.0
        elif any(x in low for x in CORRECTION_MARKERS):
            kind="correction";score=-.35
        else:
            return None
        # Explicit playbook id can target older routines.
        pid=None
        m=re.search(r"(workplace\.[a-z0-9_.-]+|custom\.[a-z0-9_.-]+)",low)
        if m:
            pid=m.group(1)
        return {"event_type":kind,"score":score,"text":raw,"playbook_id":pid}

    def rate_response(self,query,positive=True,note="",project_id=None):
        query=str(query or "").strip()
        playbook_id=None
        category=None
        match=None
        if self.workplace and query:
            try:
                found=self.workplace.search(query,limit=1).get("items",[])
                if found and float(found[0].get("score",0))>=8:
                    match=found[0]
                    playbook_id=match.get("id")
                    category=match.get("category")
            except Exception:
                pass
        event_type="positive_feedback" if positive else "negative_feedback"
        event=self.record_event(
            event_type,
            source_type="message_rating",
            playbook_id=playbook_id,
            category=category,
            project_id=project_id,
            query=query,
            note=str(note or ("Resposta marcada como útil." if positive else "Resposta marcada como não útil.")),
            score=1.0 if positive else -1.0,
            metadata={"inferred_playbook":bool(playbook_id),"match_score":(match or {}).get("score")},
        )
        if playbook_id and not positive:
            key=self._profile_key("playbook",playbook_id)
            with self._connect() as c:
                row=c.execute(
                    "SELECT failure_streak FROM competence_profiles WHERE competence_key=?",
                    (key,)
                ).fetchone()
            if row and int(row["failure_streak"] or 0)>=self.failure_threshold:
                self.propose_adaptation(
                    playbook_id,
                    reason="A abordagem recebeu avaliações negativas repetidas em respostas relacionadas.",
                    rule_text="Antes de repetir esta rotina, revise o pedido original e valide se o playbook realmente é adequado ao objetivo.",
                    source_event_id=event["id"],
                    confidence=.76,
                    auto_approve_soft=False,
                )
        return {"ok":True,"event":event,"playbook_id":playbook_id,"matched":match}

    def observe_feedback(self,text,project_id=None):
        parsed=self.parse_feedback(text)
        if not parsed:
            return {"ok":True,"recognized":False}
        recent=None
        playbook_id=parsed.get("playbook_id")
        if not playbook_id:
            recent=self._resolve_recent_playbook()
            playbook_id=(recent or {}).get("playbook_id")
        category=None
        if playbook_id and self.workplace:
            got=self.workplace.get(playbook_id)
            if got.get("ok"):
                category=got["data"].get("category")
        event=self.record_event(
            parsed["event_type"],
            source_type="conversation_feedback",
            source_id=(recent or {}).get("id"),
            playbook_id=playbook_id,
            category=category,
            project_id=project_id,
            query=text,
            note=parsed["text"],
            score=parsed["score"],
            metadata={"recent_usage":recent or {}},
        )
        result={"ok":True,"recognized":True,"event":event,"playbook_id":playbook_id}

        if playbook_id and parsed["event_type"] in {"negative_feedback","correction"}:
            # Explicit user corrections are safe as soft prompt guidance. They do
            # not install code or execute external actions.
            auto = self.auto_soft_rules and parsed["event_type"]=="correction"
            candidate=self.propose_adaptation(
                playbook_id,
                reason=parsed["text"],
                rule_text=f"Na próxima execução, considere esta correção do usuário: {parsed['text']}",
                source_event_id=event["id"],
                confidence=.93 if parsed["event_type"]=="correction" else .78,
                auto_approve_soft=auto,
            )
            result["adaptation"]=candidate

        if playbook_id and parsed["event_type"]=="negative_feedback":
            key=self._profile_key("playbook",playbook_id)
            with self._connect() as c:
                row=c.execute(
                    "SELECT failures,corrections,failure_streak FROM competence_profiles WHERE competence_key=?",
                    (key,)
                ).fetchone()
            if row and int(row["failure_streak"] or 0)>=self.failure_threshold:
                self.propose_adaptation(
                    playbook_id,
                    reason=f"Falhas consecutivas detectadas ({int(row['failure_streak'])}). Revisar o fluxo antes de repetir.",
                    rule_text="Antes de executar, revise o último erro registrado e valide premissas/fonte antes de repetir o mesmo caminho.",
                    source_event_id=event["id"],
                    confidence=.82,
                    auto_approve_soft=False,
                )
        return result

    def record_playbook_outcome(self,playbook_id,status,note="",query="",job_id=None,project_id=None):
        status=str(status or "").lower()
        event_type="success" if status in {"completed","success","ok"} else "failure" if status in {"failed","failure","error"} else "waiting"
        score=1.0 if event_type=="success" else -1.0 if event_type=="failure" else -.1
        category=None
        agents=[]
        if self.workplace:
            got=self.workplace.get(playbook_id)
            if got.get("ok"):
                category=got["data"].get("category")
                agents=list(got["data"].get("agents") or [])
        event = self.record_event(
            event_type,
            source_type="long_horizon",
            source_id=job_id,
            playbook_id=playbook_id,
            category=category,
            project_id=project_id,
            query=query,
            note=note,
            score=score,
            metadata={"job_id":job_id,"status":status},
        )

        for agent_id in agents:
            try:
                self._update_profile(
                    "agent", agent_id, agent_id,
                    "success" if event_type=="success" else "failure" if event_type=="failure" else "neutral"
                )
            except Exception:
                pass

        if event_type=="failure":
            key=self._profile_key("playbook",playbook_id)
            with self._connect() as c:
                row=c.execute(
                    "SELECT failure_streak FROM competence_profiles WHERE competence_key=?",
                    (key,)
                ).fetchone()
            if row and int(row["failure_streak"] or 0)>=self.failure_threshold:
                self.propose_adaptation(
                    playbook_id,
                    reason=(
                        f"O playbook falhou {int(row['failure_streak'])} vez(es) consecutivas. "
                        f"Último erro: {str(note)[:1200]}"
                    ),
                    rule_text=(
                        "Antes de repetir esta rotina, valide o pré-requisito que falhou, "
                        "confira a fonte/aba correta e tente uma alternativa segura se o mesmo caminho falhar novamente."
                    ),
                    source_event_id=event["id"],
                    confidence=.84,
                    auto_approve_soft=False,
                )
        return event

    def retrospective(self,limit=40):
        events=self.recent_events(limit=limit).get("items",[])
        profiles=self.competence_map(limit=200).get("items",[])
        proposed=self.candidates("proposed",limit=30).get("items",[])
        successes=sum(1 for x in events if x.get("score",0)>.2)
        failures=sum(1 for x in events if x.get("score",0)<-.2)
        corrections=sum(1 for x in events if x.get("event_type") in {"correction","negative_feedback"})
        strongest=profiles[:5]
        weakest=sorted(profiles,key=lambda x:(x.get("confidence",.5),-x.get("uses",0)))[:5]
        return {
            "ok":True,
            "window":len(events),
            "successes":successes,
            "failures":failures,
            "corrections":corrections,
            "success_rate":round(successes/max(1,successes+failures)*100,1),
            "strongest":strongest,
            "weakest":weakest,
            "pending_adaptations":proposed,
        }

    def context(self,query,project_id=None,limit=5,max_chars=3200):
        tokens=set(re.findall(r"[a-zà-ÿ0-9_-]{3,}",str(query or "").lower()))
        profiles=self.competence_map(limit=150).get("items",[])
        scored=[]
        for item in profiles:
            hay=(str(item.get("label",""))+" "+str(item.get("competence_key",""))).lower()
            score=sum(1 for t in tokens if t in hay)
            if score:
                scored.append((score,item))
        scored.sort(key=lambda x:(-x[0],-x[1].get("uses",0)))
        parts=[]
        for _,item in scored[:int(limit)]:
            parts.append(
                f"- {item['label']}: confiança {round(float(item['confidence'])*100)}%, "
                f"{item['successes']} sucesso(s), {item['failures']} falha(s), {item['corrections']} correção(ões)."
            )
        if not parts:
            return {"ok":True,"text":"","items":[]}
        return {"ok":True,"text":("EXPERIÊNCIA RELEVANTE\n"+"\n".join(parts))[:int(max_chars)],"items":[x[1] for x in scored[:int(limit)]]}

    def stats(self):
        with self._connect() as c:
            events=c.execute("SELECT COUNT(*) n FROM experience_events").fetchone()["n"]
            rules=c.execute("SELECT COUNT(*) n FROM playbook_rules WHERE active=1").fetchone()["n"]
            candidates=c.execute("SELECT status,COUNT(*) n FROM adaptation_candidates GROUP BY status").fetchall()
            profiles=c.execute("SELECT COUNT(*) n FROM competence_profiles").fetchone()["n"]
        return {
            "ok":True,
            "events":int(events),
            "active_rules":int(rules),
            "competences":int(profiles),
            "candidates":{x["status"]:int(x["n"]) for x in candidates},
        }
