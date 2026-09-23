import json
import hashlib
import time
import urllib.parse
import urllib.request
import urllib.error
import sqlite3
from pathlib import Path
from capabilities.openapi_importer import import_openapi_json, save_imported


class CapabilityHub:
    def __init__(self, catalog_path, cache_dir, user_catalog_path=None, user_agent="JarvisLocal/0.6"):
        self.catalog_path = Path(catalog_path)
        self.user_catalog_path = Path(user_catalog_path) if user_catalog_path else self.catalog_path.with_name("user_catalog.json")
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.user_agent = user_agent
        self._catalog = []
        self._by_id = {}
        self.reload()
        self._last_request = {}
        self.usage_db = self.cache_dir / "usage.db"
        self._init_usage_db()



    def _init_usage_db(self):
        with sqlite3.connect(self.usage_db) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS capability_usage (
                    capability_id TEXT PRIMARY KEY,
                    calls INTEGER NOT NULL DEFAULT 0,
                    successes INTEGER NOT NULL DEFAULT 0,
                    failures INTEGER NOT NULL DEFAULT 0,
                    avg_latency REAL NOT NULL DEFAULT 0,
                    last_used REAL
                )
            """)

    def _record_usage(self, capability_id, ok, latency):
        try:
            with sqlite3.connect(self.usage_db) as conn:
                row = conn.execute(
                    "SELECT calls,successes,failures,avg_latency FROM capability_usage WHERE capability_id=?",
                    (capability_id,)
                ).fetchone()
                if row:
                    calls, successes, failures, avg = row
                    new_calls = calls + 1
                    new_avg = ((avg * calls) + float(latency)) / new_calls
                    conn.execute(
                        "UPDATE capability_usage SET calls=?,successes=?,failures=?,avg_latency=?,last_used=? WHERE capability_id=?",
                        (new_calls, successes + (1 if ok else 0), failures + (0 if ok else 1), new_avg, time.time(), capability_id)
                    )
                else:
                    conn.execute(
                        "INSERT INTO capability_usage(capability_id,calls,successes,failures,avg_latency,last_used) VALUES(?,?,?,?,?,?)",
                        (capability_id, 1, 1 if ok else 0, 0 if ok else 1, float(latency), time.time())
                    )
        except Exception:
            pass

    def usage_stats(self, capability_id=None, limit=20):
        try:
            with sqlite3.connect(self.usage_db) as conn:
                conn.row_factory = sqlite3.Row
                if capability_id:
                    row = conn.execute("SELECT * FROM capability_usage WHERE capability_id=?", (capability_id,)).fetchone()
                    return dict(row) if row else None
                rows = conn.execute(
                    "SELECT * FROM capability_usage ORDER BY calls DESC, successes DESC LIMIT ?", (int(limit),)
                ).fetchall()
                return [dict(r) for r in rows]
        except Exception:
            return [] if capability_id is None else None

    def reload(self):
        builtins = json.loads(self.catalog_path.read_text(encoding="utf-8"))
        users = []
        if self.user_catalog_path.exists():
            try:
                users = json.loads(self.user_catalog_path.read_text(encoding="utf-8"))
            except Exception:
                users = []
        merged = {item["id"]: item for item in builtins if item.get("id")}
        for item in users:
            if isinstance(item, dict) and item.get("id"):
                merged[item["id"]] = item
        self._catalog = sorted(merged.values(), key=lambda x: x["id"])
        self._by_id = {item["id"]: item for item in self._catalog}


    def discover_public_apis(self, query, limit=8):
        result = self.execute("apiguru.list", {}, timeout=30)
        if not result.get("ok"):
            return result
        data = result.get("data") or {}
        q = str(query).strip().lower()
        terms = [x for x in q.split() if len(x) >= 2]
        ranked=[]
        if isinstance(data, dict):
            for api_id, record in data.items():
                if not isinstance(record, dict):
                    continue
                versions = record.get("versions") or {}
                preferred = record.get("preferred")
                ver = versions.get(preferred) if preferred else None
                if not ver and versions:
                    ver = list(versions.values())[-1]
                if not isinstance(ver, dict):
                    continue
                info = ver.get("info") or {}
                title = str(info.get("title") or api_id)
                desc = str(info.get("description") or "")
                hay = f"{api_id} {title} {desc}".lower()
                score = (8 if q and q in hay else 0) + sum(2 for t in terms if t in hay)
                if score <= 0:
                    continue
                spec_url = ver.get("swaggerUrl") or ver.get("swaggerYamlUrl")
                if not spec_url or not str(spec_url).lower().endswith(('.json','swagger.json','openapi.json')):
                    # APIs.guru swaggerUrl is typically JSON even when the suffix is generic; keep https URLs.
                    if not str(spec_url or '').startswith('https://'):
                        continue
                ranked.append((score, {
                    "api_id": api_id,
                    "title": title,
                    "version": preferred,
                    "description": desc[:500],
                    "spec_url": spec_url,
                }))
        ranked.sort(key=lambda x: (-x[0], x[1]["title"]))
        return {"ok": True, "items": [x[1] for x in ranked[:int(limit)]], "count": len(ranked)}

    def import_openapi(self, spec_url, prefix="imported", max_operations=60):
        result = import_openapi_json(spec_url, prefix=prefix, max_operations=max_operations, user_agent=self.user_agent)
        if not result.get("ok"):
            return result
        total = save_imported(self.user_catalog_path, result.get("capabilities", []))
        self.reload()
        return {"ok": True, "imported": result.get("count", 0), "user_capabilities": total, "title": result.get("title")}

    def get(self, capability_id):
        return self._by_id.get(str(capability_id))

    def stats(self):
        providers = {}
        groups = {}
        for item in self._catalog:
            providers[item["provider"]] = providers.get(item["provider"], 0) + 1
            groups[item["group"]] = groups.get(item["group"], 0) + 1
        return {
            "ok": True,
            "capabilities": len(self._catalog),
            "providers": providers,
            "groups": groups,
        }

    def list(self, provider=None, group=None, limit=100):
        items = self._catalog
        if provider:
            items = [x for x in items if x["provider"].lower() == str(provider).lower()]
        if group:
            items = [x for x in items if x["group"].lower() == str(group).lower()]
        return {"ok": True, "items": items[: int(limit)], "count": len(items)}

    def search(self, query, limit=12):
        q = str(query).strip().lower()
        if not q:
            return {"ok": True, "items": [], "count": 0}
        terms = [t for t in q.replace("/", " ").replace("_", " ").split() if len(t) >= 2]
        ranked = []
        for item in self._catalog:
            hay = " ".join([
                item.get("id", ""), item.get("provider", ""), item.get("group", ""),
                item.get("description", ""), " ".join(item.get("keywords", []))
            ]).lower()
            score = 0
            if q in hay:
                score += 8
            for term in terms:
                if term in hay:
                    score += 2
            if score:
                usage = self.usage_stats(item.get("id"))
                if usage and usage.get("calls", 0):
                    ratio = usage.get("successes", 0) / max(1, usage.get("calls", 0))
                    score += min(3.0, ratio * 2.0 + min(1.0, usage.get("calls", 0) / 10.0))
                ranked.append((score, item))
        ranked.sort(key=lambda x: (-x[0], x[1]["id"]))
        items = [item for _, item in ranked[: int(limit)]]
        # Keep tool result compact but include parameter schema.
        compact = []
        for item in items:
            compact.append({
                "id": item["id"],
                "provider": item["provider"],
                "group": item["group"],
                "description": item["description"],
                "params": item.get("params", {}),
            })
        return {"ok": True, "items": compact, "count": len(ranked)}

    def _cache_path(self, url):
        key = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{key}.json"

    def _rate_limit(self, provider, min_interval):
        now = time.monotonic()
        previous = self._last_request.get(provider, 0.0)
        delay = float(min_interval or 0) - (now - previous)
        if delay > 0:
            time.sleep(delay)
        self._last_request[provider] = time.monotonic()

    def _prepare_url(self, item, params):
        params = dict(params or {})
        url = item["url"]
        specs = item.get("params", {})
        query = dict(item.get("fixed_query", {}))

        for name, spec in specs.items():
            required = bool(spec.get("required", False))
            location = spec.get("in", "query")
            value = params.get(name, spec.get("default"))
            if required and (value is None or str(value) == ""):
                raise ValueError(f"Parâmetro obrigatório ausente: {name}")
            if value is None:
                continue
            if location == "path":
                url = url.replace("{" + name + "}", urllib.parse.quote(str(value), safe=""))
            else:
                query[spec.get("name", name)] = value

        # Allow explicitly whitelisted extra query parameters.
        allowed_extra = set(item.get("allow_extra_query", []))
        for name in allowed_extra:
            if name in params and params[name] is not None:
                query[name] = params[name]

        if query:
            encoded = urllib.parse.urlencode(query, doseq=True)
            url += ("&" if "?" in url else "?") + encoded
        return url

    def execute(self, capability_id, params=None, timeout=20, force_refresh=False):
        started = time.monotonic()
        item = self._by_id.get(str(capability_id))
        if not item:
            return {"ok": False, "error": f"Capacidade não encontrada: {capability_id}"}
        if item.get("auth") not in (None, "none"):
            return {"ok": False, "error": "Esta capacidade exige autenticação e está desativada no modo 100% gratuito/anônimo."}

        try:
            url = self._prepare_url(item, params or {})
        except Exception as exc:
            return {"ok": False, "error": str(exc), "capability": capability_id}

        ttl = int(item.get("cache_ttl", 300))
        cache_path = self._cache_path(url)
        if not force_refresh and cache_path.exists() and ttl > 0:
            try:
                cached = json.loads(cache_path.read_text(encoding="utf-8"))
                if time.time() - cached.get("ts", 0) <= ttl:
                    payload = cached.get("payload")
                    result = {
                        "ok": True, "capability": capability_id, "provider": item["provider"],
                        "url": url, "cached": True, "data": payload,
                    }
                    self._record_usage(capability_id, True, time.monotonic() - started)
                    return result
            except Exception:
                pass

        self._rate_limit(item["provider"], item.get("min_interval", 0.25))
        headers = {
            "User-Agent": self.user_agent,
            "Accept": item.get("accept", "application/json, text/plain;q=0.8, */*;q=0.5"),
        }
        headers.update(item.get("headers", {}))
        req = urllib.request.Request(url, headers=headers, method=item.get("method", "GET"))

        try:
            with urllib.request.urlopen(req, timeout=float(timeout)) as resp:
                raw = resp.read(int(item.get("max_bytes", 5_000_000)))
                ctype = (resp.headers.get("Content-Type") or "").lower()
                charset = resp.headers.get_content_charset() or "utf-8"
                text = raw.decode(charset, errors="replace")
                if "json" in ctype or item.get("response") == "json":
                    try:
                        payload = json.loads(text)
                    except Exception:
                        payload = {"raw": text[:30000]}
                else:
                    payload = {"text": text[:30000]}
        except urllib.error.HTTPError as exc:
            body = exc.read(4000).decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
            result = {"ok": False, "error": f"HTTP {exc.code}: {body[:1200]}", "capability": capability_id, "url": url}
            self._record_usage(capability_id, False, time.monotonic() - started)
            return result
        except Exception as exc:
            result = {"ok": False, "error": str(exc), "capability": capability_id, "url": url}
            self._record_usage(capability_id, False, time.monotonic() - started)
            return result

        try:
            cache_path.write_text(json.dumps({"ts": time.time(), "payload": payload}, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

        result = {
            "ok": True, "capability": capability_id, "provider": item["provider"],
            "url": url, "cached": False, "data": payload,
        }
        self._record_usage(capability_id, True, time.monotonic() - started)
        return result
