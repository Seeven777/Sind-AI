import json
import re
import time
import urllib.parse
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup


class WebsiteInspector:
    def __init__(self, user_agent="JarvisSindPet/0.7"):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})

    def _get(self, url, timeout=20):
        url = str(url).strip()
        if not url.startswith(("https://", "http://")):
            url = "https://" + url

        started = time.monotonic()
        r = self.session.get(url, timeout=timeout, allow_redirects=True)
        elapsed = round((time.monotonic() - started) * 1000, 1)
        return r, elapsed

    def fetch(self, url):
        try:
            r, elapsed = self._get(url)
            return {
                "ok": True,
                "status": r.status_code,
                "url": r.url,
                "elapsed_ms": elapsed,
                "content_type": r.headers.get("content-type", ""),
                "bytes": len(r.content),
                "text": r.text[:16000],
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _page(self, url):
        r, elapsed = self._get(url)
        soup = BeautifulSoup(r.text, "html.parser")
        return r, soup, elapsed

    def execute(self, operation, **params):
        url = params.pop("url", "")
        if operation == "fetch":
            return self.fetch(url)
        return self.check(operation, url, **params)

    def check(self, operation, url, **params):
        try:
            if operation == "robots_txt":
                base = urllib.parse.urlsplit(url if "://" in str(url) else "https://" + str(url))
                target = f"{base.scheme}://{base.netloc}/robots.txt"
                r, elapsed = self._get(target)
                return {"ok": True, "status": r.status_code, "url": r.url, "elapsed_ms": elapsed, "text": r.text[:12000]}

            if operation == "sitemap_xml":
                base = urllib.parse.urlsplit(url if "://" in str(url) else "https://" + str(url))
                target = f"{base.scheme}://{base.netloc}/sitemap.xml"
                r, elapsed = self._get(target)
                urls = []
                if r.ok:
                    try:
                        root = ET.fromstring(r.text)
                        for node in root.iter():
                            if node.tag.endswith("loc") and node.text:
                                urls.append(node.text.strip())
                    except Exception:
                        pass
                return {"ok": True, "status": r.status_code, "url": r.url, "elapsed_ms": elapsed, "items": urls[:200], "count": len(urls)}

            r, soup, elapsed = self._page(url)
            html = r.text
            final_url = r.url

            if operation == "status":
                return {"ok": True, "status": r.status_code, "url": final_url}
            if operation == "response_time":
                return {"ok": True, "elapsed_ms": elapsed, "url": final_url}
            if operation == "headers":
                return {"ok": True, "headers": dict(r.headers), "url": final_url}
            if operation == "content_type":
                return {"ok": True, "value": r.headers.get("content-type", "")}
            if operation == "html_size":
                return {"ok": True, "bytes": len(r.content)}
            if operation == "title":
                return {"ok": True, "value": soup.title.get_text(" ", strip=True) if soup.title else ""}
            if operation == "meta_description":
                n = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
                return {"ok": True, "value": n.get("content", "").strip() if n else ""}
            if operation == "canonical":
                n = soup.find("link", attrs={"rel": lambda v: v and "canonical" in (v if isinstance(v, list) else [v])})
                return {"ok": True, "value": urllib.parse.urljoin(final_url, n.get("href", "")) if n else ""}
            if operation == "robots_meta":
                n = soup.find("meta", attrs={"name": re.compile("^robots$", re.I)})
                return {"ok": True, "value": n.get("content", "").strip() if n else ""}
            if operation == "noindex":
                n = soup.find("meta", attrs={"name": re.compile("^robots$", re.I)})
                value = (n.get("content", "") if n else "").lower()
                return {"ok": True, "noindex": "noindex" in value}
            if operation == "viewport":
                n = soup.find("meta", attrs={"name": re.compile("^viewport$", re.I)})
                return {"ok": True, "value": n.get("content", "") if n else ""}
            if operation == "charset":
                return {"ok": True, "value": r.encoding or soup.original_encoding or ""}
            if operation == "language":
                return {"ok": True, "value": (soup.html.get("lang", "") if soup.html else "")}
            if operation == "headings":
                items = [{"level": h.name, "text": h.get_text(" ", strip=True)} for h in soup.find_all(re.compile("^h[1-6]$"))]
                return {"ok": True, "items": items, "count": len(items)}
            if operation == "h1_count":
                items = [h.get_text(" ", strip=True) for h in soup.find_all("h1")]
                return {"ok": True, "count": len(items), "items": items}
            if operation == "images":
                items = []
                for img in soup.find_all("img"):
                    items.append({
                        "src": urllib.parse.urljoin(final_url, img.get("src", "")),
                        "alt": img.get("alt"),
                        "loading": img.get("loading", ""),
                        "width": img.get("width"),
                        "height": img.get("height"),
                    })
                return {"ok": True, "items": items[:300], "count": len(items)}
            if operation == "missing_alt":
                items = [
                    urllib.parse.urljoin(final_url, img.get("src", ""))
                    for img in soup.find_all("img")
                    if img.get("alt") is None
                ]
                return {"ok": True, "items": items[:300], "count": len(items)}
            if operation == "empty_alt":
                items = [
                    urllib.parse.urljoin(final_url, img.get("src", ""))
                    for img in soup.find_all("img")
                    if img.get("alt") == ""
                ]
                return {"ok": True, "items": items[:300], "count": len(items)}
            if operation in {"links", "internal_links", "external_links"}:
                host = urllib.parse.urlsplit(final_url).netloc.lower()
                items = []
                for a in soup.find_all("a", href=True):
                    href = urllib.parse.urljoin(final_url, a.get("href", ""))
                    parsed = urllib.parse.urlsplit(href)
                    if parsed.scheme not in {"http", "https"}:
                        continue
                    internal = parsed.netloc.lower() == host
                    if operation == "internal_links" and not internal:
                        continue
                    if operation == "external_links" and internal:
                        continue
                    items.append({"text": a.get_text(" ", strip=True), "url": href, "internal": internal})
                return {"ok": True, "items": items[:500], "count": len(items)}
            if operation == "forms":
                items = []
                for f in soup.find_all("form"):
                    fields = f.find_all(["input", "textarea", "select"])
                    items.append({
                        "action": urllib.parse.urljoin(final_url, f.get("action", "")),
                        "method": f.get("method", "get").upper(),
                        "fields": len(fields),
                    })
                return {"ok": True, "items": items, "count": len(items)}
            if operation == "form_labels":
                ids = {x.get("for") for x in soup.find_all("label") if x.get("for")}
                controls = [x for x in soup.find_all(["input", "textarea", "select"]) if (x.get("type") or "").lower() != "hidden"]
                unlabeled = []
                for c in controls:
                    cid = c.get("id")
                    aria = c.get("aria-label") or c.get("aria-labelledby")
                    if not aria and (not cid or cid not in ids):
                        unlabeled.append({"tag": c.name, "name": c.get("name", ""), "id": cid or "", "type": c.get("type", "")})
                return {"ok": True, "items": unlabeled[:200], "count": len(unlabeled)}
            if operation == "scripts":
                items = [urllib.parse.urljoin(final_url, x.get("src", "")) for x in soup.find_all("script", src=True)]
                return {"ok": True, "items": items, "count": len(items)}
            if operation == "stylesheets":
                items = [urllib.parse.urljoin(final_url, x.get("href", "")) for x in soup.find_all("link", href=True) if "stylesheet" in (x.get("rel") or [])]
                return {"ok": True, "items": items, "count": len(items)}
            if operation == "jsonld":
                items = []
                for n in soup.find_all("script", attrs={"type": "application/ld+json"}):
                    raw = n.string or n.get_text()
                    try:
                        items.append(json.loads(raw))
                    except Exception:
                        items.append(raw[:2000])
                return {"ok": True, "items": items, "count": len(items)}
            if operation == "open_graph":
                data = {n.get("property"): n.get("content", "") for n in soup.find_all("meta", property=re.compile("^og:"))}
                return {"ok": True, "data": data}
            if operation == "twitter_cards":
                data = {n.get("name"): n.get("content", "") for n in soup.find_all("meta", attrs={"name": re.compile("^twitter:")})}
                return {"ok": True, "data": data}
            if operation == "hreflang":
                items = [{"lang": x.get("hreflang", ""), "href": urllib.parse.urljoin(final_url, x.get("href", ""))} for x in soup.find_all("link", hreflang=True)]
                return {"ok": True, "items": items, "count": len(items)}
            if operation == "favicon":
                n = soup.find("link", rel=lambda v: v and any("icon" in x for x in (v if isinstance(v, list) else [v])))
                return {"ok": True, "value": urllib.parse.urljoin(final_url, n.get("href", "")) if n else ""}
            if operation == "rss_feeds":
                items = []
                for x in soup.find_all("link", href=True):
                    typ = (x.get("type") or "").lower()
                    if "rss" in typ or "atom" in typ:
                        items.append({"title": x.get("title", ""), "type": typ, "url": urllib.parse.urljoin(final_url, x.get("href", ""))})
                return {"ok": True, "items": items, "count": len(items)}
            if operation == "word_count":
                text = soup.get_text(" ", strip=True)
                words = re.findall(r"\b[\wÀ-ÿ'-]+\b", text)
                return {"ok": True, "count": len(words)}
            if operation == "reading_time":
                text = soup.get_text(" ", strip=True)
                words = re.findall(r"\b[\wÀ-ÿ'-]+\b", text)
                return {"ok": True, "words": len(words), "minutes": round(len(words) / 200, 2)}
            if operation == "text_preview":
                text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True)).strip()
                return {"ok": True, "text": text[:int(params.get("max_chars", 5000))]}
            if operation == "emails":
                found = sorted(set(re.findall(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", html)))
                return {"ok": True, "items": found, "count": len(found)}
            if operation == "phones":
                text = soup.get_text(" ", strip=True)
                found = sorted(set(re.findall(r"(?:\+?55\s*)?(?:\(?\d{2}\)?\s*)?\d{4,5}[-.\s]?\d{4}", text)))
                return {"ok": True, "items": found[:100], "count": len(found)}
            if operation == "social_links":
                domains = ("instagram.com", "facebook.com", "linkedin.com", "youtube.com", "tiktok.com", "x.com", "twitter.com")
                items = []
                for a in soup.find_all("a", href=True):
                    href = urllib.parse.urljoin(final_url, a.get("href", ""))
                    if any(d in href.lower() for d in domains):
                        items.append(href)
                items = sorted(set(items))
                return {"ok": True, "items": items, "count": len(items)}
            if operation == "mixed_content":
                if not final_url.startswith("https://"):
                    return {"ok": True, "items": [], "count": 0, "note": "Página não está em HTTPS."}
                refs = []
                for tag, attr in (("img","src"),("script","src"),("link","href"),("iframe","src")):
                    for n in soup.find_all(tag):
                        val = n.get(attr)
                        if val and val.startswith("http://"):
                            refs.append(val)
                return {"ok": True, "items": refs[:300], "count": len(refs)}
            if operation == "security_headers":
                wanted = [
                    "content-security-policy", "strict-transport-security",
                    "x-content-type-options", "x-frame-options",
                    "referrer-policy", "permissions-policy"
                ]
                data = {k: r.headers.get(k, "") for k in wanted}
                return {"ok": True, "headers": data, "missing": [k for k,v in data.items() if not v]}
            if operation == "cache_headers":
                keys = ["cache-control", "etag", "last-modified", "expires", "age"]
                return {"ok": True, "headers": {k: r.headers.get(k, "") for k in keys}}
            if operation == "server_header":
                return {"ok": True, "value": r.headers.get("server", "")}
            if operation == "content_encoding":
                return {"ok": True, "value": r.headers.get("content-encoding", "")}
            if operation == "mobile_ready":
                viewport = soup.find("meta", attrs={"name": re.compile("^viewport$", re.I)})
                return {"ok": True, "mobile_ready": bool(viewport and "width=device-width" in viewport.get("content", "").lower())}
            if operation == "link_text_quality":
                generic = {"clique aqui", "saiba mais", "aqui", "link", "mais"}
                bad = []
                for a in soup.find_all("a", href=True):
                    txt = re.sub(r"\s+", " ", a.get_text(" ", strip=True)).strip().lower()
                    if not txt or txt in generic:
                        bad.append({"text": txt, "url": urllib.parse.urljoin(final_url, a.get("href", ""))})
                return {"ok": True, "items": bad[:200], "count": len(bad)}
            if operation == "button_names":
                bad = []
                for b in soup.find_all(["button", "input"]):
                    if b.name == "input" and (b.get("type") or "").lower() not in {"button","submit","reset"}:
                        continue
                    name = (b.get_text(" ", strip=True) or b.get("value") or b.get("aria-label") or "").strip()
                    if not name:
                        bad.append(str(b)[:300])
                return {"ok": True, "unnamed_count": len(bad), "items": bad[:100]}
            if operation == "seo_summary":
                title = soup.title.get_text(" ", strip=True) if soup.title else ""
                md = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
                desc = md.get("content", "").strip() if md else ""
                h1s = [h.get_text(" ", strip=True) for h in soup.find_all("h1")]
                imgs = soup.find_all("img")
                missing_alt = sum(1 for x in imgs if x.get("alt") is None)
                return {
                    "ok": True,
                    "title": title,
                    "title_length": len(title),
                    "description": desc,
                    "description_length": len(desc),
                    "h1_count": len(h1s),
                    "h1": h1s[:5],
                    "images": len(imgs),
                    "missing_alt": missing_alt,
                    "canonical": bool(soup.find("link", rel=lambda v: v and "canonical" in (v if isinstance(v,list) else [v]))),
                    "elapsed_ms": elapsed,
                    "status": r.status_code,
                }

            return {"ok": False, "error": f"Operação de website desconhecida: {operation}"}

        except Exception as exc:
            return {"ok": False, "error": str(exc), "operation": operation}
