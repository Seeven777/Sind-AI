import json
from pathlib import Path
import re
import unicodedata



_SEARCH_STOPWORDS = {
    "a","o","as","os","um","uma","uns","umas","de","da","do","das","dos","e","em",
    "no","na","nos","nas","para","por","sobre","com","sem","ao","aos","à","às",
    "relacionado","relacionados","relacionada","relacionadas","disponivel","disponiveis",
    "criar","configurar","administrar","mostrar","mostre","procure","buscar","busque",
}
_SEARCH_SYNONYMS = {
    "automacao":{"automation","scheduler","agenda","agendamento"},
    "automacoes":{"automation","scheduler","agenda","agendamento"},
    "monitorar":{"monitor","monitoramento","watch","website"},
    "monitoramento":{"monitor","watch"},
    "site":{"site","website","web"},
    "aprovacao":{"approval","governance"},
    "aprovacoes":{"approval","governance"},
    "integracao":{"connector","api"},
    "integracoes":{"connector","api"},
    "api":{"api","connector","endpoint"},
    "usuario":{"user","team"},
    "usuarios":{"user","team"},
    "permissao":{"grant","acesso","permission","role"},
    "permissoes":{"grant","acesso","permission","role"},
    "equipe":{"team","portal"},
    "assistente":{"assistant","portal","team"},
    "lacuna":{"gap","knowledge"},
    "lacunas":{"gap","knowledge"},
    "conhecimento":{"knowledge"},
    "qualidade":{"quality","feedback"},
    "treinamento":{"training","track"},
}

def _norm_search(value):
    s = unicodedata.normalize("NFKD", str(value or "").lower())
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[^a-z0-9_.-]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def _singularish(token):
    if len(token) > 5 and token.endswith("oes"):
        return token[:-3] + "ao"
    if len(token) > 4 and token.endswith("s"):
        return token[:-1]
    return token

def _search_terms(query):
    normalized = _norm_search(query)
    raw = [x for x in normalized.replace("_", " ").split() if len(x) >= 2]
    terms = []
    for token in raw:
        if token in _SEARCH_STOPWORDS:
            continue
        base = _singularish(token)
        terms.append(base)
        for extra in _SEARCH_SYNONYMS.get(token, set()) | _SEARCH_SYNONYMS.get(base, set()):
            terms.append(_norm_search(extra))
    return normalized, list(dict.fromkeys(x for x in terms if x))


class ActionHub:
    """
    Broker local de ações. Mantém centenas de operações fora do schema do LLM.
    O modelo usa somente search_actions + execute_action.
    """

    def __init__(self, catalog_path, engines):
        self.catalog_path = Path(catalog_path)
        self.engines = dict(engines)
        self._catalog = []
        self._by_id = {}
        self.reload()

    def reload(self):
        data = json.loads(self.catalog_path.read_text(encoding="utf-8"))
        self._catalog = data.get("actions", data if isinstance(data, list) else [])
        self._by_id = {x["id"]: x for x in self._catalog}

    def get(self, action_id):
        return self._by_id.get(str(action_id))

    def stats(self):
        engines = {}
        groups = {}
        risks = {}
        for item in self._catalog:
            engines[item["engine"]] = engines.get(item["engine"], 0) + 1
            groups[item["group"]] = groups.get(item["group"], 0) + 1
            risks[item.get("risk","read")] = risks.get(item.get("risk","read"), 0) + 1
        return {
            "ok": True,
            "actions": len(self._catalog),
            "engines": engines,
            "groups": groups,
            "risks": risks,
        }

    def list(self, engine=None, group=None, limit=100):
        items = self._catalog
        if engine:
            items = [x for x in items if x["engine"].lower() == str(engine).lower()]
        if group:
            items = [x for x in items if x["group"].lower() == str(group).lower()]
        return {"ok": True, "items": items[:int(limit)], "count": len(items)}

    def search(self, query, limit=15):
        q, terms = _search_terms(query)
        if not q:
            return {"ok": True, "items": [], "count": 0}

        ranked = []
        for item in self._catalog:
            hay = _norm_search(" ".join([
                item.get("id",""), item.get("engine",""), item.get("group",""),
                item.get("description",""), " ".join(item.get("keywords",[]))
            ]))
            score = 12 if q in hay else 0
            matched = 0
            for term in terms:
                if term and term in hay:
                    score += 3
                    matched += 1
            score += matched * matched
            if score:
                ranked.append((score, item))

        ranked.sort(key=lambda x: (-x[0], x[1]["id"]))

        compact = []
        for _, item in ranked[:int(limit)]:
            compact.append({
                "id": item["id"],
                "engine": item["engine"],
                "group": item["group"],
                "description": item["description"],
                "risk": item.get("risk","read"),
                "params": item.get("params",{}),
            })
        return {"ok": True, "items": compact, "count": len(ranked)}

    def execute(self, action_id, params=None):
        item = self.get(action_id)
        if not item:
            return {"ok": False, "error": f"Ação não encontrada: {action_id}"}

        engine_name = item["engine"]
        engine = self.engines.get(engine_name)
        if engine is None:
            return {"ok": False, "error": f"Engine não disponível: {engine_name}"}

        params = dict(params or {})
        required = [
            name for name, spec in item.get("params",{}).items()
            if spec.get("required")
        ]
        missing = [name for name in required if params.get(name) in (None,"")]
        if missing:
            return {
                "ok": False,
                "error": "Parâmetros obrigatórios ausentes: " + ", ".join(missing),
                "action": action_id,
            }

        operation = item["operation"]

        try:
            if hasattr(engine, "execute"):
                result = engine.execute(operation, **params)
            elif hasattr(engine, operation):
                result = getattr(engine, operation)(**params)
            else:
                return {"ok": False, "error": f"Operação não implementada: {operation}"}
        except Exception as exc:
            result = {"ok": False, "error": str(exc)}

        if not isinstance(result, dict):
            result = {"ok": True, "data": result}

        result.setdefault("action", action_id)
        result.setdefault("engine", engine_name)
        return result
