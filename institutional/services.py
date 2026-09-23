import json
import re
import webbrowser
from pathlib import Path


class InstitutionalServices:
    """Mapa de serviços cotidianos do SindPetshop-SP sem armazenar credenciais."""

    def __init__(self, registry_path):
        self.registry_path = Path(registry_path)
        data = json.loads(self.registry_path.read_text(encoding="utf-8"))
        self.items = data.get("services", [])
        self.by_id = {x["id"]: x for x in self.items}
        self._tab_opener = None
        self._tab_action = None


    def set_tab_adapter(self, opener=None, action=None):
        """Conecta o registry às abas embutidas da UI sem acoplá-lo ao Qt."""
        self._tab_opener = opener
        self._tab_action = action
        return {"ok": True, "embedded_tabs": bool(opener)}

    def tab_action(self, query, operation="inspect", **kwargs):
        resolved = self.resolve(query)
        if not resolved.get("ok"):
            return resolved
        item = resolved["data"]
        if not self._tab_action:
            return {
                "ok": False,
                "error": "As abas institucionais ainda não estão conectadas à interface.",
                "service": item["id"],
            }
        try:
            result = self._tab_action(item["id"], operation, kwargs)
            if isinstance(result, dict):
                result.setdefault("service", item["id"])
                result.setdefault("name", item["name"])
                result.setdefault("url", item["url"])
                result.setdefault("embedded", True)
                return result
            return {"ok": True, "result": result, "service": item["id"], "name": item["name"], "url": item["url"]}
        except Exception as exc:
            return {"ok": False, "error": str(exc), "service": item["id"]}

    def list(self, kind=None, daily=None):
        items = list(self.items)
        if kind:
            items = [x for x in items if x.get("kind") == kind]
        if daily is not None:
            items = [x for x in items if bool(x.get("daily")) == bool(daily)]
        return {"ok": True, "items": items, "count": len(items)}

    def resolve(self, query):
        q = str(query or "").strip().lower()
        if not q:
            return {"ok": False, "error": "Informe o serviço."}
        ranked = []
        for item in self.items:
            hay = " ".join([
                item.get("id",""), item.get("name",""), item.get("kind",""),
                " ".join(item.get("aliases", [])), item.get("notes","")
            ]).lower()
            score = 20 if q == item.get("id","").lower() else 0
            if q in hay:
                score += 12
            for token in re.findall(r"[a-zà-ÿ0-9_-]{2,}", q):
                if token in hay:
                    score += 2
            if score:
                ranked.append((score, item))
        ranked.sort(key=lambda x: (-x[0], x[1]["id"]))
        if not ranked:
            return {"ok": False, "error": f"Serviço não encontrado: {query}"}
        return {"ok": True, "data": ranked[0][1], "matches": [x[1] for x in ranked[:5]]}

    def open(self, query):
        resolved = self.resolve(query)
        if not resolved.get("ok"):
            return resolved
        item = resolved["data"]

        # Prefer the persistent embedded tab when the desktop UI is available.
        if self._tab_opener:
            try:
                result = self._tab_opener(item["id"])
                if isinstance(result, dict) and not result.get("ok", True):
                    return result
                return {
                    "ok": True,
                    "service": item["id"],
                    "name": item["name"],
                    "url": item["url"],
                    "embedded": True,
                }
            except Exception:
                pass

        try:
            webbrowser.open(item["url"])
            return {"ok": True, "service": item["id"], "name": item["name"], "url": item["url"], "embedded": False}
        except Exception as exc:
            return {"ok": False, "error": str(exc), "service": item["id"]}

    def context(self, query, limit=5):
        q = str(query or "").lower()
        scored = []
        for item in self.items:
            hay = " ".join([
                item.get("id",""), item.get("name",""), item.get("kind",""),
                " ".join(item.get("aliases", [])), " ".join(item.get("capabilities", [])),
                item.get("notes","")
            ]).lower()
            score = sum(1 for t in re.findall(r"[a-zà-ÿ0-9_-]{3,}", q) if t in hay)
            if score:
                scored.append((score, item))
        scored.sort(key=lambda x: (-x[0], x[1]["id"]))
        return {"ok": True, "items": [x[1] for x in scored[:int(limit)]], "count": len(scored)}


    def parse_open_command(self, text):
        t = str(text or "").strip().lower()
        if not re.match(r"^\s*(abra|abrir|acesse|acessar|entre|ir para|vá para|va para)\b", t):
            return None
        for item in self.items:
            aliases = [item.get("id",""), item.get("name","")] + list(item.get("aliases",[]))
            for alias in aliases:
                a = str(alias).strip().lower()
                if a and a in t:
                    return {"operation":"open","query":a,"service":item["id"]}
        return None

    def stats(self):
        kinds = {}
        for x in self.items:
            kinds[x.get("kind","other")] = kinds.get(x.get("kind","other"), 0) + 1
        return {"ok": True, "services": len(self.items), "daily": sum(1 for x in self.items if x.get("daily")), "kinds": kinds}
