import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path

class LearningJournal:
    """Aprendizado persistente por experiência e correções explícitas, sem retreino de pesos."""
    def __init__(self, db_path):
        self.db_path=Path(db_path);self.db_path.parent.mkdir(parents=True,exist_ok=True);self._init_db()
    def _connect(self):
        c=sqlite3.connect(self.db_path,timeout=20);c.row_factory=sqlite3.Row;return c
    def _now(self): return datetime.now().isoformat(timespec="seconds")
    def _init_db(self):
        with self._connect() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS cognitive_episodes(
              id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,user_text TEXT NOT NULL,
              answer TEXT NOT NULL DEFAULT '',status TEXT NOT NULL DEFAULT 'completed',metadata_json TEXT NOT NULL DEFAULT '{}');
            CREATE TABLE IF NOT EXISTS cognitive_lessons(
              id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
              kind TEXT NOT NULL,trigger_text TEXT NOT NULL,lesson TEXT NOT NULL,confidence REAL NOT NULL DEFAULT 0.8,
              status TEXT NOT NULL DEFAULT 'active',occurrences INTEGER NOT NULL DEFAULT 1);
            CREATE INDEX IF NOT EXISTS idx_lessons_status ON cognitive_lessons(status,kind);
            """)
            try:c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS cognitive_lessons_fts USING fts5(lesson,trigger_text,lesson_id UNINDEXED)")
            except sqlite3.OperationalError:pass
    def record_episode(self,user_text,answer,status="completed",metadata=None):
        with self._connect() as c:
            cur=c.execute("INSERT INTO cognitive_episodes(created_at,user_text,answer,status,metadata_json) VALUES(?,?,?,?,?)",
                          (self._now(),str(user_text),str(answer)[:12000],str(status),json.dumps(metadata or {},ensure_ascii=False,default=str)))
        return {"ok":True,"id":int(cur.lastrowid)}
    def _extract_explicit_lesson(self,text):
        raw=re.sub(r"\s+"," ",str(text or "")).strip();low=raw.lower()
        patterns=[
          (r"^(?:prefiro|eu prefiro)\s+(.+)","preference","Preferência do usuário: {x}"),
          (r"^(?:sempre)\s+(.+)","rule","Regra solicitada pelo usuário: sempre {x}"),
          (r"^(?:nunca)\s+(.+)","rule","Regra solicitada pelo usuário: nunca {x}"),
          (r"^(?:não faça|nao faca)\s+(.+)","correction","Correção do usuário: não fazer {x}"),
          (r"^(?:da próxima vez|da proxima vez|quando eu pedir)\s+(.+)","procedure","Procedimento futuro solicitado: {x}"),
          (r"^(?:lembre que|considere que)\s+(.+)","fact","Contexto explicitamente informado: {x}"),
        ]
        for pattern,kind,template in patterns:
            m=re.match(pattern,raw,flags=re.I)
            if m:return kind,template.format(x=m.group(1).strip())
        if any(x in low for x in ["isso está errado","isso esta errado","não era isso","nao era isso"]):
            return "correction","O usuário indicou que a abordagem anterior estava incorreta; revisar o contexto antes de repetir a mesma estratégia."
        return None
    def learn_from_user(self,text):
        parsed=self._extract_explicit_lesson(text)
        if not parsed:return {"ok":True,"learned":False}
        kind,lesson=parsed;now=self._now()
        with self._connect() as c:
            row=c.execute("SELECT id,occurrences FROM cognitive_lessons WHERE status='active' AND lower(lesson)=lower(?)",(lesson,)).fetchone()
            if row:
                c.execute("UPDATE cognitive_lessons SET occurrences=occurrences+1,updated_at=? WHERE id=?",(now,int(row["id"])))
                return {"ok":True,"learned":True,"id":int(row["id"]),"lesson":lesson,"occurrences":int(row["occurrences"])+1}
            cur=c.execute("INSERT INTO cognitive_lessons(created_at,updated_at,kind,trigger_text,lesson,confidence,status) VALUES(?,?,?,?,?,?,?)",
                          (now,now,kind,str(text),lesson,0.95,"active"));lid=int(cur.lastrowid)
            try:c.execute("INSERT INTO cognitive_lessons_fts(lesson,trigger_text,lesson_id) VALUES(?,?,?)",(lesson,str(text),lid))
            except sqlite3.OperationalError:pass
        return {"ok":True,"learned":True,"id":lid,"lesson":lesson,"occurrences":1}
    def relevant(self,query,limit=5):
        tokens=re.findall(r"[A-Za-zÀ-ÿ0-9_-]{3,}",str(query or "").lower())[:8]
        if not tokens:return []
        fts=" OR ".join(f'"{x}"' for x in tokens)
        with self._connect() as c:
            try:
                rows=c.execute("""SELECT l.* FROM cognitive_lessons_fts f JOIN cognitive_lessons l ON l.id=f.lesson_id
                                  WHERE cognitive_lessons_fts MATCH ? AND l.status='active'
                                  ORDER BY bm25(cognitive_lessons_fts),l.confidence DESC LIMIT ?""",(fts,int(limit))).fetchall()
            except sqlite3.OperationalError:
                rows=c.execute("SELECT * FROM cognitive_lessons WHERE status='active' ORDER BY updated_at DESC LIMIT ?",(int(limit),)).fetchall()
        return [dict(r) for r in rows]
    def list_lessons(self,status="active",limit=100):
        with self._connect() as c:rows=c.execute("SELECT * FROM cognitive_lessons WHERE status=? ORDER BY updated_at DESC LIMIT ?",(str(status),int(limit))).fetchall()
        return {"ok":True,"items":[dict(r) for r in rows],"count":len(rows)}
    def stats(self):
        with self._connect() as c:
            ep=c.execute("SELECT COUNT(*) n FROM cognitive_episodes").fetchone()["n"]
            ls=c.execute("SELECT COUNT(*) n FROM cognitive_lessons WHERE status='active'").fetchone()["n"]
        return {"ok":True,"episodes":ep,"active_lessons":ls}
