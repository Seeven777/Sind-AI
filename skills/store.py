import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path


def slugify(text):
    text = str(text).strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text or "skill"


class SkillStore:
    def __init__(self, base_dir):
        self.base_dir = Path(base_dir).resolve()
        self.library_dir = self.base_dir / "library"
        self.library_dir.mkdir(parents=True, exist_ok=True)

        self.action_log = self.base_dir / "action_history.jsonl"
        if not self.action_log.exists():
            self.action_log.write_text("", encoding="utf-8")

    def _skill_path(self, name):
        return self.library_dir / f"{slugify(name)}.json"

    def log_action(self, tool, args, result=None, source="user"):
        entry = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "tool": str(tool),
            "args": args or {},
            "source": source,
            "ok": bool((result or {}).get("ok", False)),
        }

        with self.action_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        return entry

    def recent_actions(self, count=10, only_success=True):
        count = max(1, min(int(count), 100))

        try:
            lines = self.action_log.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError:
            return []

        items = []

        for line in reversed(lines):
            if not line.strip():
                continue

            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue

            if only_success and not item.get("ok"):
                continue

            items.append(item)

            if len(items) >= count:
                break

        return list(reversed(items))

    def save_skill(self, name, steps, description="", inputs=None, metadata=None):
        name = str(name).strip().rstrip(" .!?;,:")
        if not name:
            return {"ok": False, "error": "Nome da skill vazio."}

        clean_steps = []

        for step in steps:
            tool = step.get("tool")
            args = step.get("args", {})

            if not tool:
                continue

            clean_steps.append({
                "tool": tool,
                "args": args,
            })

        if not clean_steps:
            return {"ok": False, "error": "Nenhuma ação válida para salvar."}

        now = datetime.now().isoformat(timespec="seconds")
        path = self._skill_path(name)

        created_at = now
        if path.exists():
            try:
                old = json.loads(path.read_text(encoding="utf-8"))
                created_at = old.get("created_at", now)
            except Exception:
                pass

        data = {
            "version": 3 if metadata else (2 if inputs else 1),
            "name": name,
            "slug": slugify(name),
            "description": str(description).strip(),
            "created_at": created_at,
            "updated_at": now,
            "inputs": inputs or {},
            "metadata": metadata or {},
            "steps": clean_steps,
        }

        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return {
            "ok": True,
            "name": name,
            "path": str(path),
            "steps": len(clean_steps),
        }


    def save_parametric_skill(self, name, steps, inputs=None, description="", metadata=None):
        return self.save_skill(
            name=name,
            steps=steps,
            description=description,
            inputs=inputs or {},
            metadata=metadata or {},
        )

    def save_recipe_skill(self, name, steps, inputs=None, description="", metadata=None):
        """Save a declarative acquired skill with provenance/test metadata."""
        meta = dict(metadata or {})
        meta.setdefault("skill_type", "acquired_recipe")
        return self.save_skill(
            name=name,
            steps=steps,
            description=description,
            inputs=inputs or {},
            metadata=meta,
        )

    def render_skill(self, skill, values=None):
        values = dict(values or {})
        required = [
            key for key, spec in (skill.get("inputs") or {}).items()
            if spec.get("required") and values.get(key) in (None, "")
        ]
        if required:
            return {
                "ok": False,
                "error": "Entradas obrigatórias ausentes: " + ", ".join(required),
            }

        def render_value(value):
            if isinstance(value, str):
                out = value
                for key, replacement in values.items():
                    out = out.replace("{{" + str(key) + "}}", str(replacement))
                return out
            if isinstance(value, dict):
                return {k: render_value(v) for k,v in value.items()}
            if isinstance(value, list):
                return [render_value(v) for v in value]
            return value

        return {
            "ok": True,
            "steps": [
                {
                    "tool": step.get("tool"),
                    "args": render_value(step.get("args", {})),
                }
                for step in skill.get("steps", [])
            ],
            "inputs": skill.get("inputs", {}),
        }

    def save_from_recent_actions(self, name, count):
        actions = self.recent_actions(count=count, only_success=True)

        if len(actions) < count:
            return {
                "ok": False,
                "error": f"Encontrei apenas {len(actions)} ação(ões) recente(s)."
            }

        steps = [
            {
                "tool": item["tool"],
                "args": item.get("args", {}),
            }
            for item in actions
        ]

        return self.save_skill(
            name=name,
            steps=steps,
            description=f"Criada a partir das últimas {count} ações executadas.",
        )

    def list_skills(self):
        skills = []

        for path in sorted(self.library_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue

            skills.append({
                "name": data.get("name", path.stem),
                "slug": data.get("slug", path.stem),
                "description": data.get("description", ""),
                "steps": len(data.get("steps", [])),
                "updated_at": data.get("updated_at", ""),
                "inputs": list((data.get("inputs") or {}).keys()),
                "metadata": data.get("metadata") or {},
                "path": str(path),
            })

        return skills

    def get_skill(self, name):
        wanted = str(name).strip().rstrip(" .!?;,:").lower()

        # Exact slug path first.
        direct = self._skill_path(wanted)
        if direct.exists():
            try:
                return json.loads(direct.read_text(encoding="utf-8"))
            except Exception:
                return None

        # Fallback by human name.
        for item in self.list_skills():
            if item["name"].lower() == wanted or item["slug"].lower() == slugify(wanted):
                try:
                    return json.loads(Path(item["path"]).read_text(encoding="utf-8"))
                except Exception:
                    return None

        return None

    def delete_skill(self, name):
        skill = self.get_skill(name)
        if not skill:
            return {"ok": False, "error": "Skill não encontrada."}

        path = self._skill_path(skill["name"])
        if path.exists():
            path.unlink()

        return {"ok": True, "name": skill["name"]}


    def relevant_skills(self, query, limit=5):
        q = str(query or "").lower()
        tokens = set(re.findall(r"[a-z0-9_]{3,}", slugify(q)))
        scored = []
        for item in self.list_skills():
            hay = " ".join([
                str(item.get("name", "")), str(item.get("slug", "")),
                str(item.get("description", "")), " ".join(item.get("inputs", []) or []),
            ]).lower()
            score = 0
            name = str(item.get("name", "")).lower()
            if name and name in q:
                score += 12
            score += sum(1 for tok in tokens if tok and tok in slugify(hay))
            if score >= 2:
                scored.append((score, item))
        scored.sort(key=lambda x: (-x[0], x[1].get("name", "")))
        return [item for _, item in scored[:int(limit)]]

    def relevant_context(self, query, limit=3):
        items = self.relevant_skills(query, limit=limit)
        if not items:
            return {"items": [], "text": ""}
        lines = []
        for item in items:
            inputs = item.get("inputs") or []
            inp = f" | entradas: {', '.join(inputs)}" if inputs else ""
            lines.append(f"- {item.get('name')} ({item.get('steps')} passos){inp}: {item.get('description','')}")
        return {"items": items, "text": "SKILLS APRENDIDAS RELEVANTES:\n" + "\n".join(lines)}

    def catalog_for_prompt(self, limit=30):
        items = self.list_skills()[:limit]
        if not items:
            return ""

        lines = []
        for item in items:
            desc = f" — {item['description']}" if item["description"] else ""
            inputs = item.get("inputs") or []
            inp = f" | entradas: {', '.join(inputs)}" if inputs else ""
            lines.append(f"- {item['name']} ({item['steps']} passos){inp}{desc}")

        return "\nSkills disponíveis:\n" + "\n".join(lines)
