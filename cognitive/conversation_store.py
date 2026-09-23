import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path

STOPWORDS = {
    "a","o","as","os","um","uma","de","da","do","das","dos","e","em","no","na","nos","nas",
    "para","por","com","sem","que","como","qual","quais","isso","isto","eu","meu","minha","se",
    "ao","aos","à","às","sobre","mais","menos","muito","muita","ser","ter","foi","está","esta"
}

class ConversationStore:
    """Histórico conversacional persistente com recuperação FTS5 leve."""
    def __init__(self, db_path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self.current_session_id = self._latest_session_id() or self.new_session()["session_id"]

    def _connect(self):
        conn = sqlite3.connect(self.db_path, timeout=20)
        conn.row_factory = sqlite3.Row
        return conn

    def _now(self):
        return datetime.now().isoformat(timespec="seconds")

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversation_sessions(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL DEFAULT 'Nova conversa',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                archived INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS conversation_messages(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY(session_id) REFERENCES conversation_sessions(id)
            );
            CREATE INDEX IF NOT EXISTS idx_conv_messages_session ON conversation_messages(session_id,id);
            """)
            try:
                conn.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS conversation_fts
                              USING fts5(content, session_id UNINDEXED, message_id UNINDEXED, role UNINDEXED);""")
            except sqlite3.OperationalError:
                pass

    def _latest_session_id(self):
        with self._connect() as conn:
            row = conn.execute("SELECT id FROM conversation_sessions WHERE archived=0 ORDER BY updated_at DESC,id DESC LIMIT 1").fetchone()
        return int(row["id"]) if row else None

    def new_session(self, title=None):
        now = self._now()
        with self._connect() as conn:
            cur = conn.execute("INSERT INTO conversation_sessions(title,created_at,updated_at) VALUES(?,?,?)",
                               (str(title or "Nova conversa")[:160], now, now))
            sid = int(cur.lastrowid)
        self.current_session_id = sid
        return {"ok": True, "session_id": sid, "title": title or "Nova conversa"}

    def set_current(self, session_id):
        with self._connect() as conn:
            row = conn.execute("SELECT id FROM conversation_sessions WHERE id=?", (int(session_id),)).fetchone()
        if not row:
            return {"ok": False, "error": "Conversa não encontrada."}
        self.current_session_id = int(session_id)
        return {"ok": True, "session_id": int(session_id)}

    def append(self, role, content, metadata=None, session_id=None):
        content = str(content or "").strip()
        if not content:
            return {"ok": False, "error": "Mensagem vazia."}
        sid = int(session_id or self.current_session_id)
        now = self._now()
        with self._connect() as conn:
            cur = conn.execute("INSERT INTO conversation_messages(session_id,role,content,created_at,metadata_json) VALUES(?,?,?,?,?)",
                               (sid, str(role), content, now, json.dumps(metadata or {}, ensure_ascii=False, default=str)))
            mid = int(cur.lastrowid)
            conn.execute("UPDATE conversation_sessions SET updated_at=? WHERE id=?", (now, sid))
            try:
                conn.execute("INSERT INTO conversation_fts(content,session_id,message_id,role) VALUES(?,?,?,?)",
                             (content, sid, mid, str(role)))
            except sqlite3.OperationalError:
                pass
            if role == "user":
                sess = conn.execute("SELECT title FROM conversation_sessions WHERE id=?", (sid,)).fetchone()
                if sess and sess["title"] == "Nova conversa":
                    title = re.sub(r"\s+", " ", content).strip()[:80]
                    conn.execute("UPDATE conversation_sessions SET title=? WHERE id=?", (title, sid))
        return {"ok": True, "message_id": mid, "session_id": sid}

    def recent_messages(self, limit=10, session_id=None):
        sid = int(session_id or self.current_session_id)
        with self._connect() as conn:
            rows = conn.execute("SELECT id,role,content,created_at,metadata_json FROM conversation_messages WHERE session_id=? ORDER BY id DESC LIMIT ?",
                                (sid, int(limit))).fetchall()
        items=[]
        for row in reversed(rows):
            d=dict(row)
            try: d["metadata"] = json.loads(d.pop("metadata_json") or "{}")
            except Exception: d["metadata"] = {}
            items.append(d)
        return items

    def _tokens(self, query):
        words = re.findall(r"[A-Za-zÀ-ÿ0-9_.:-]+", str(query).lower())
        return [w for w in words if len(w)>=3 and w not in STOPWORDS]

    def search(self, query, limit=6, session_id=None, all_sessions=True):
        query=str(query or "").strip()
        if not query: return {"ok": True, "items": [], "count": 0}
        tokens=self._tokens(query)[:8]
        if not tokens: return {"ok": True, "items": [], "count": 0}
        fts_query=" OR ".join(f'"{t}"' for t in tokens)
        sid=int(session_id or self.current_session_id)
        with self._connect() as conn:
            try:
                sql=("SELECT f.content,f.session_id,f.message_id,f.role,bm25(conversation_fts) score,m.created_at "
                     "FROM conversation_fts f JOIN conversation_messages m ON m.id=f.message_id WHERE conversation_fts MATCH ? ")
                args=[fts_query]
                if not all_sessions:
                    sql+="AND f.session_id=? ";args.append(sid)
                sql+="ORDER BY score LIMIT ?";args.append(int(limit))
                items=[dict(r) for r in conn.execute(sql,args).fetchall()]
            except sqlite3.OperationalError:
                like="%"+"%".join(tokens[:3])+"%"
                sql="SELECT content,session_id,id message_id,role,created_at FROM conversation_messages WHERE lower(content) LIKE lower(?)"
                args=[like]
                if not all_sessions: sql+=" AND session_id=?";args.append(sid)
                sql+=" ORDER BY id DESC LIMIT ?";args.append(int(limit))
                items=[dict(r) for r in conn.execute(sql,args).fetchall()]
        return {"ok":True,"items":items,"count":len(items)}

    def context_messages(self, query, recent_limit=6, relevant_limit=4, max_chars=3600):
        recent=self.recent_messages(limit=recent_limit)
        relevant=self.search(query,limit=relevant_limit,all_sessions=True).get("items",[])
        seen={(x.get("role"),x.get("content")) for x in recent}
        merged=list(recent)
        for item in reversed(relevant):
            key=(item.get("role"),item.get("content"))
            if key not in seen and item.get("content"):
                merged.insert(0,{"role":item.get("role","user"),"content":item["content"]});seen.add(key)
        out=[];chars=0
        for item in reversed(merged):
            content=str(item.get("content",""))
            if chars+len(content)>int(max_chars) and out: continue
            out.append({"role":item.get("role","user"),"content":content});chars+=len(content)
        return list(reversed(out))

    def list_sessions(self, limit=30):
        with self._connect() as conn:
            rows=conn.execute("""SELECT s.id,s.title,s.created_at,s.updated_at,s.archived,COUNT(m.id) message_count
                                 FROM conversation_sessions s LEFT JOIN conversation_messages m ON m.session_id=s.id
                                 WHERE s.archived=0 GROUP BY s.id ORDER BY s.updated_at DESC LIMIT ?""",
                              (int(limit),)).fetchall()
        return {"ok":True,"items":[dict(r) for r in rows],"count":len(rows),"current":self.current_session_id}


    def delete_session(self, session_id):
        """Exclui permanentemente uma conversa e suas mensagens/índice FTS."""
        sid = int(session_id)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id,title FROM conversation_sessions WHERE id=?",
                (sid,)
            ).fetchone()
            if not row:
                return {"ok": False, "error": "Conversa não encontrada."}

            message_rows = conn.execute(
                "SELECT id FROM conversation_messages WHERE session_id=?",
                (sid,)
            ).fetchall()
            message_ids = [int(x["id"]) for x in message_rows]

            try:
                conn.execute("DELETE FROM conversation_fts WHERE session_id=?", (sid,))
            except sqlite3.OperationalError:
                # FTS é opcional.
                pass

            conn.execute("DELETE FROM conversation_messages WHERE session_id=?", (sid,))
            conn.execute("DELETE FROM conversation_sessions WHERE id=?", (sid,))

        if self.current_session_id == sid:
            next_id = self._latest_session_id()
            if next_id:
                self.current_session_id = next_id
            else:
                created = self.new_session()
                self.current_session_id = int(created["session_id"])

        return {
            "ok": True,
            "deleted_session_id": sid,
            "deleted_messages": len(message_ids),
            "current": self.current_session_id,
        }

    def stats(self):
        with self._connect() as conn:
            sessions=conn.execute("SELECT COUNT(*) n FROM conversation_sessions WHERE archived=0").fetchone()["n"]
            messages=conn.execute("SELECT COUNT(*) n FROM conversation_messages").fetchone()["n"]
        return {"ok":True,"sessions":sessions,"messages":messages,"current":self.current_session_id}
