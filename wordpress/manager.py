import json
from pathlib import Path
import mimetypes
import re
import requests


class WordPressManager:
    def __init__(self, profiles_path):
        self.profiles_path = Path(profiles_path)
        self.profiles_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.profiles_path.exists():
            self.profiles_path.write_text('{"profiles":{}}', encoding="utf-8")

    def _load(self):
        try:
            return json.loads(self.profiles_path.read_text(encoding="utf-8"))
        except Exception:
            return {"profiles": {}}

    def list_profiles(self):
        data = self._load().get("profiles", {})
        return {
            "ok": True,
            "items": [
                {"name": name, "site_url": p.get("site_url"), "username": p.get("username")}
                for name, p in sorted(data.items())
            ],
            "count": len(data),
        }

    def profile(self, name):
        p = self._load().get("profiles", {}).get(str(name))
        if not p:
            raise RuntimeError(f"Perfil WordPress não encontrado: {name}")
        return p

    def _auth(self, profile_name):
        p = self.profile(profile_name)
        try:
            import keyring
        except Exception as exc:
            raise RuntimeError("Pacote keyring não instalado.") from exc
        password = keyring.get_password("JarvisWordPress", str(profile_name))
        if not password:
            raise RuntimeError(
                f"Credencial do perfil '{profile_name}' não encontrada. "
                "Execute configure_wordpress.bat."
            )
        return (p.get("username", ""), password)

    def _base(self, profile_name):
        p = self.profile(profile_name)
        site = str(p.get("site_url", "")).rstrip("/")
        if not site.startswith("https://"):
            raise RuntimeError("Por segurança, apenas WordPress em HTTPS é aceito.")
        return site + "/wp-json/wp/v2"

    def _request(self, profile, method, route, params=None, data=None, files=None, auth=True, timeout=30):
        base = self._base(profile)
        url = base + "/" + route.lstrip("/")
        credentials = self._auth(profile) if auth else None
        r = requests.request(
            method=method,
            url=url,
            params=params,
            json=data if files is None else None,
            files=files,
            auth=credentials,
            timeout=timeout,
            headers={"User-Agent": "JarvisSindPet/0.7"},
        )
        try:
            payload = r.json()
        except Exception:
            payload = r.text[:12000]
        if not r.ok:
            return {"ok": False, "status": r.status_code, "error": payload, "url": url}
        return {"ok": True, "status": r.status_code, "data": payload, "url": url}

    def discover(self, site_url):
        site = str(site_url).rstrip("/")
        if not site.startswith("https://"):
            return {"ok": False, "error": "Somente HTTPS."}
        try:
            r = requests.get(site + "/wp-json/", timeout=20, headers={"User-Agent":"JarvisSindPet/0.7"})
            payload = r.json()
            return {
                "ok": r.ok,
                "status": r.status_code,
                "name": payload.get("name"),
                "description": payload.get("description"),
                "url": payload.get("url"),
                "namespaces": payload.get("namespaces", []),
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def execute(self, operation, **params):
        profile = params.pop("profile", "default")

        if operation == "profiles":
            return self.list_profiles()

        if operation == "discover":
            return self.discover(params.get("site_url", ""))

        if operation == "auth_status":
            try:
                auth = self._auth(profile)
                return {"ok": True, "configured": bool(auth[0] and auth[1]), "profile": profile}
            except Exception as exc:
                return {"ok": True, "configured": False, "profile": profile, "detail": str(exc)}

        list_routes = {
            "list_posts": "posts",
            "list_pages": "pages",
            "list_media": "media",
            "list_categories": "categories",
            "list_tags": "tags",
            "list_comments": "comments",
            "list_users": "users",
            "list_types": "types",
            "list_statuses": "statuses",
            "list_taxonomies": "taxonomies",
            "list_search": "search",
        }
        if operation in list_routes:
            q = {}
            for key in (
                "page","per_page","search","after","before","orderby","order",
                "status","slug","categories","tags","author","parent","type","subtype"
            ):
                if key in params and params[key] not in (None, ""):
                    q[key] = params[key]
            return self._request(profile, "GET", list_routes[operation], params=q, auth=False)

        get_routes = {
            "get_post": "posts/{id}",
            "get_page": "pages/{id}",
            "get_media": "media/{id}",
            "get_category": "categories/{id}",
            "get_tag": "tags/{id}",
            "get_comment": "comments/{id}",
            "get_user": "users/{id}",
        }
        if operation in get_routes:
            route = get_routes[operation].format(id=int(params["id"]))
            return self._request(profile, "GET", route, auth=False)

        if operation in {"create_post_draft","create_page_draft"}:
            route = "posts" if "post" in operation else "pages"
            body = {
                "title": params.get("title", ""),
                "content": params.get("content", ""),
                "excerpt": params.get("excerpt", ""),
                "status": "draft",
            }
            for key in ("slug","featured_media","parent","template","comment_status","ping_status"):
                if params.get(key) not in (None, ""):
                    body[key] = params[key]
            if params.get("categories") is not None:
                body["categories"] = params["categories"]
            if params.get("tags") is not None:
                body["tags"] = params["tags"]
            return self._request(profile, "POST", route, data=body, auth=True)

        if operation in {"update_post","update_page"}:
            route = ("posts" if "post" in operation else "pages") + f"/{int(params['id'])}"
            allowed = {
                "title","content","excerpt","slug","status","featured_media",
                "categories","tags","parent","template","comment_status","ping_status","date"
            }
            body = {k:v for k,v in params.items() if k in allowed and v is not None}
            return self._request(profile, "POST", route, data=body, auth=True)

        if operation in {"publish_post","publish_page","unpublish_post","unpublish_page"}:
            is_post = "post" in operation
            route = ("posts" if is_post else "pages") + f"/{int(params['id'])}"
            status = "publish" if operation.startswith("publish") else "draft"
            return self._request(profile, "POST", route, data={"status":status}, auth=True)

        if operation in {"schedule_post","schedule_page"}:
            route = ("posts" if "post" in operation else "pages") + f"/{int(params['id'])}"
            return self._request(
                profile, "POST", route,
                data={"status":"future", "date":params["date"]},
                auth=True
            )

        if operation in {"trash_post","trash_page","delete_post","delete_page"}:
            route = ("posts" if "post" in operation else "pages") + f"/{int(params['id'])}"
            force = operation.startswith("delete")
            return self._request(profile, "DELETE", route, params={"force":"true" if force else "false"}, auth=True)

        if operation == "create_category":
            return self._request(profile, "POST", "categories", data={
                "name": params["name"],
                "slug": params.get("slug"),
                "description": params.get("description",""),
                "parent": params.get("parent",0),
            }, auth=True)

        if operation == "create_tag":
            return self._request(profile, "POST", "tags", data={
                "name": params["name"],
                "slug": params.get("slug"),
                "description": params.get("description",""),
            }, auth=True)

        if operation == "update_category":
            body = {k:v for k,v in params.items() if k in {"name","slug","description","parent"} and v is not None}
            return self._request(profile, "POST", f"categories/{int(params['id'])}", data=body, auth=True)

        if operation == "update_tag":
            body = {k:v for k,v in params.items() if k in {"name","slug","description"} and v is not None}
            return self._request(profile, "POST", f"tags/{int(params['id'])}", data=body, auth=True)

        if operation in {"delete_category","delete_tag"}:
            route = ("categories" if "category" in operation else "tags") + f"/{int(params['id'])}"
            return self._request(profile, "DELETE", route, params={"force":"true"}, auth=True)

        if operation == "upload_media":
            path = Path(params["path"]).expanduser().resolve()
            if not path.is_file():
                return {"ok": False, "error": "Arquivo de mídia não encontrado."}
            mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
            auth = self._auth(profile)
            url = self._base(profile) + "/media"
            with path.open("rb") as fh:
                r = requests.post(
                    url,
                    files={"file": (path.name, fh, mime)},
                    data={
                        "title": params.get("title", ""),
                        "alt_text": params.get("alt_text", ""),
                        "caption": params.get("caption", ""),
                        "description": params.get("description", ""),
                    },
                    auth=auth,
                    timeout=60,
                    headers={"User-Agent":"JarvisSindPet/0.7"},
                )
            try:
                data = r.json()
            except Exception:
                data = r.text
            return {"ok": r.ok, "status": r.status_code, "data": data if r.ok else None, "error": None if r.ok else data}

        if operation == "update_media":
            body = {k:v for k,v in params.items() if k in {"title","alt_text","caption","description","post"} and v is not None}
            return self._request(profile, "POST", f"media/{int(params['id'])}", data=body, auth=True)

        if operation == "delete_media":
            return self._request(profile, "DELETE", f"media/{int(params['id'])}", params={"force":"true"}, auth=True)

        if operation == "set_featured_media_post":
            return self._request(profile, "POST", f"posts/{int(params['id'])}", data={"featured_media":int(params["media_id"])}, auth=True)

        if operation == "set_featured_media_page":
            return self._request(profile, "POST", f"pages/{int(params['id'])}", data={"featured_media":int(params["media_id"])}, auth=True)

        if operation == "site_settings":
            return self._request(profile, "GET", "settings", auth=True)

        if operation == "update_settings":
            allowed = {"title","description","url","email","timezone","date_format","time_format","start_of_week","language","use_smilies","default_category","default_post_format","posts_per_page"}
            body = {k:v for k,v in params.items() if k in allowed and v is not None}
            return self._request(profile, "POST", "settings", data=body, auth=True)

        return {"ok": False, "error": f"Operação WordPress desconhecida: {operation}"}
