import json
import re
import time
from pathlib import Path


class BrowserAgent:
    """
    Browser dedicado do Jarvis usando Playwright + Microsoft Edge instalado.
    Mantém um perfil separado e persistente, permitindo login manual sem o Jarvis
    precisar armazenar senhas.
    """

    def __init__(self, profile_dir, downloads_dir):
        self.profile_dir = Path(profile_dir)
        self.downloads_dir = Path(downloads_dir)
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.downloads_dir.mkdir(parents=True, exist_ok=True)

        self._pw = None
        self.context = None
        self.page = None

    def _ensure(self):
        if self.context is not None:
            try:
                if self.pages():
                    if self.page is None or self.page.is_closed():
                        self.page = self.context.pages[-1]
                    return
            except Exception:
                pass

        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:
            raise RuntimeError(
                "Playwright não está instalado. Execute install.bat."
            ) from exc

        self._pw = sync_playwright().start()

        errors = []
        for channel in ("msedge", "chrome"):
            try:
                self.context = self._pw.chromium.launch_persistent_context(
                    user_data_dir=str(self.profile_dir),
                    channel=channel,
                    headless=False,
                    accept_downloads=True,
                    downloads_path=str(self.downloads_dir),
                    viewport={"width": 1365, "height": 768},
                    args=[
                        "--disable-background-networking",
                        "--disable-component-update",
                    ],
                )
                break
            except Exception as exc:
                errors.append(f"{channel}: {exc}")
                self.context = None

        if self.context is None:
            try:
                self._pw.stop()
            except Exception:
                pass
            self._pw = None
            raise RuntimeError(
                "Não consegui iniciar Microsoft Edge/Chrome pelo Playwright. "
                + " | ".join(errors[-2:])
            )

        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()

    def start(self):
        self._ensure()
        return {
            "ok": True,
            "pages": len(self.context.pages),
            "url": self.page.url,
            "title": self._safe_title(),
        }

    def stop(self):
        try:
            if self.context:
                self.context.close()
        finally:
            self.context = None
            self.page = None
            if self._pw:
                try:
                    self._pw.stop()
                except Exception:
                    pass
            self._pw = None
        return {"ok": True}

    def status(self):
        if self.context is None:
            return {"ok": True, "running": False, "pages": 0}
        try:
            pages = self.context.pages
            return {
                "ok": True,
                "running": True,
                "pages": len(pages),
                "url": self.page.url if self.page else None,
                "title": self._safe_title(),
            }
        except Exception:
            return {"ok": True, "running": False, "pages": 0}

    def _safe_title(self):
        try:
            return self.page.title() if self.page else ""
        except Exception:
            return ""

    def pages(self):
        self._ensure()
        return [
            {
                "index": i,
                "url": p.url,
                "title": self._title_of(p),
                "active": p == self.page,
            }
            for i, p in enumerate(self.context.pages)
        ]

    def _title_of(self, page):
        try:
            return page.title()
        except Exception:
            return ""

    def new_tab(self, url=None):
        self._ensure()
        self.page = self.context.new_page()
        if url:
            self.page.goto(str(url), wait_until="domcontentloaded", timeout=30000)
        return {"ok": True, "index": len(self.context.pages)-1, "url": self.page.url}

    def switch_tab(self, index):
        self._ensure()
        pages = self.context.pages
        idx = int(index)
        if idx < 0 or idx >= len(pages):
            return {"ok": False, "error": "Índice de aba inválido."}
        self.page = pages[idx]
        self.page.bring_to_front()
        return {"ok": True, "index": idx, "url": self.page.url, "title": self._safe_title()}

    def close_tab(self, index=None):
        self._ensure()
        pages = self.context.pages
        target = self.page if index is None else pages[int(index)]
        target.close()
        pages = self.context.pages
        self.page = pages[-1] if pages else self.context.new_page()
        return {"ok": True, "pages": len(self.context.pages)}

    def goto(self, url):
        self._ensure()
        url = str(url).strip()
        if not re.match(r"^https?://", url, re.I):
            url = "https://" + url
        resp = self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
        return {
            "ok": True,
            "url": self.page.url,
            "title": self._safe_title(),
            "status": resp.status if resp else None,
        }

    def reload(self):
        self._ensure()
        resp = self.page.reload(wait_until="domcontentloaded", timeout=30000)
        return {"ok": True, "url": self.page.url, "status": resp.status if resp else None}

    def back(self):
        self._ensure()
        self.page.go_back(wait_until="domcontentloaded", timeout=30000)
        return {"ok": True, "url": self.page.url, "title": self._safe_title()}

    def forward(self):
        self._ensure()
        self.page.go_forward(wait_until="domcontentloaded", timeout=30000)
        return {"ok": True, "url": self.page.url, "title": self._safe_title()}

    def current_url(self):
        self._ensure()
        return {"ok": True, "url": self.page.url}

    def title(self):
        self._ensure()
        return {"ok": True, "title": self._safe_title()}

    def text(self, selector="body", max_chars=12000):
        self._ensure()
        txt = self.page.locator(selector).first.inner_text(timeout=10000)
        return {"ok": True, "text": txt[:int(max_chars)], "url": self.page.url}

    def html(self, max_chars=16000):
        self._ensure()
        html = self.page.content()
        return {"ok": True, "html": html[:int(max_chars)], "url": self.page.url}

    def links(self, limit=100):
        self._ensure()
        rows = self.page.locator("a").evaluate_all(
            """els => els.map(a => ({
                text:(a.innerText||a.getAttribute('aria-label')||'').trim(),
                href:a.href || '',
                target:a.target || ''
            }))"""
        )
        return {"ok": True, "items": rows[:int(limit)], "count": len(rows)}

    def buttons(self, limit=100):
        self._ensure()
        rows = self.page.locator("button, input[type=button], input[type=submit], [role=button]").evaluate_all(
            """els => els.map(e => ({
                text:(e.innerText||e.value||e.getAttribute('aria-label')||e.title||'').trim(),
                tag:e.tagName,
                type:e.getAttribute('type')||'',
                disabled:!!e.disabled
            }))"""
        )
        return {"ok": True, "items": rows[:int(limit)], "count": len(rows)}

    def inputs(self, limit=100):
        self._ensure()
        rows = self.page.locator("input, textarea, select, [contenteditable=true]").evaluate_all(
            """els => els.map(e => ({
                tag:e.tagName,
                type:e.getAttribute('type')||'',
                name:e.getAttribute('name')||'',
                id:e.id||'',
                placeholder:e.getAttribute('placeholder')||'',
                aria:e.getAttribute('aria-label')||'',
                autocomplete:e.getAttribute('autocomplete')||''
            }))"""
        )
        return {"ok": True, "items": rows[:int(limit)], "count": len(rows)}

    def forms(self, limit=30):
        self._ensure()
        rows = self.page.locator("form").evaluate_all(
            """els => els.map(f => ({
                action:f.action||'',
                method:(f.method||'GET').toUpperCase(),
                id:f.id||'',
                name:f.getAttribute('name')||'',
                fields:Array.from(f.querySelectorAll('input,textarea,select')).length
            }))"""
        )
        return {"ok": True, "items": rows[:int(limit)], "count": len(rows)}

    def headings(self, limit=100):
        self._ensure()
        rows = self.page.locator("h1,h2,h3,h4,h5,h6").evaluate_all(
            """els => els.map(e => ({level:e.tagName, text:(e.innerText||'').trim()}))"""
        )
        return {"ok": True, "items": rows[:int(limit)], "count": len(rows)}

    def images(self, limit=100):
        self._ensure()
        rows = self.page.locator("img").evaluate_all(
            """els => els.map(e => ({
                src:e.currentSrc||e.src||'',
                alt:e.getAttribute('alt'),
                width:e.naturalWidth||0,
                height:e.naturalHeight||0
            }))"""
        )
        return {"ok": True, "items": rows[:int(limit)], "count": len(rows)}

    def tables(self, limit=20):
        self._ensure()
        rows = self.page.locator("table").evaluate_all(
            """els => els.map(t => ({
                rows:t.rows.length,
                columns:t.rows.length ? t.rows[0].cells.length : 0,
                preview:(t.innerText||'').trim().slice(0,1200)
            }))"""
        )
        return {"ok": True, "items": rows[:int(limit)], "count": len(rows)}

    def metadata(self):
        self._ensure()
        data = self.page.evaluate(
            """() => ({
                title:document.title,
                description:document.querySelector('meta[name=description]')?.content||'',
                canonical:document.querySelector('link[rel=canonical]')?.href||'',
                lang:document.documentElement.lang||'',
                charset:document.characterSet||'',
                robots:document.querySelector('meta[name=robots]')?.content||'',
                viewport:document.querySelector('meta[name=viewport]')?.content||'',
                og:Array.from(document.querySelectorAll('meta[property^="og:"]')).map(x=>[x.getAttribute('property'),x.content]),
                twitter:Array.from(document.querySelectorAll('meta[name^="twitter:"]')).map(x=>[x.getAttribute('name'),x.content])
            })"""
        )
        return {"ok": True, "data": data, "url": self.page.url}

    def jsonld(self, limit=20):
        self._ensure()
        items = self.page.locator('script[type="application/ld+json"]').all_text_contents()
        parsed = []
        for raw in items[:int(limit)]:
            try:
                parsed.append(json.loads(raw))
            except Exception:
                parsed.append(raw[:1500])
        return {"ok": True, "items": parsed, "count": len(items)}

    def click_text(self, text, exact=False):
        self._ensure()
        loc = self.page.get_by_text(str(text), exact=bool(exact)).first
        loc.click(timeout=12000)
        return {"ok": True, "url": self.page.url}

    def click_role(self, role, name):
        self._ensure()
        self.page.get_by_role(str(role), name=str(name)).first.click(timeout=12000)
        return {"ok": True, "url": self.page.url}

    def click_selector(self, selector):
        self._ensure()
        self.page.locator(str(selector)).first.click(timeout=12000)
        return {"ok": True, "url": self.page.url}

    def _guard_sensitive_locator(self, loc):
        try:
            typ = (loc.get_attribute("type") or "").lower()
            name = " ".join([
                loc.get_attribute("name") or "",
                loc.get_attribute("id") or "",
                loc.get_attribute("placeholder") or "",
                loc.get_attribute("aria-label") or "",
            ]).lower()
        except Exception:
            typ, name = "", ""
        sensitive = ("password","senha","passcode","pin","token","secret","apikey","api_key","cvv","card")
        if typ == "password" or any(x in name for x in sensitive):
            raise RuntimeError("Campo sensível bloqueado. O Jarvis não preenche senhas, tokens ou dados de pagamento.")

    def fill_label(self, label, value):
        self._ensure()
        loc = self.page.get_by_label(str(label)).first
        self._guard_sensitive_locator(loc)
        loc.fill(str(value), timeout=12000)
        return {"ok": True}

    def fill_placeholder(self, placeholder, value):
        self._ensure()
        loc = self.page.get_by_placeholder(str(placeholder)).first
        self._guard_sensitive_locator(loc)
        loc.fill(str(value), timeout=12000)
        return {"ok": True}

    def fill_selector(self, selector, value):
        self._ensure()
        loc = self.page.locator(str(selector)).first
        self._guard_sensitive_locator(loc)
        loc.fill(str(value), timeout=12000)
        return {"ok": True}

    def type_selector(self, selector, value, delay=20):
        self._ensure()
        loc = self.page.locator(str(selector)).first
        self._guard_sensitive_locator(loc)
        loc.type(str(value), delay=int(delay), timeout=12000)
        return {"ok": True}

    def select_option(self, selector, value):
        self._ensure()
        selected = self.page.locator(str(selector)).first.select_option(str(value), timeout=12000)
        return {"ok": True, "selected": selected}

    def check(self, selector):
        self._ensure()
        self.page.locator(str(selector)).first.check(timeout=12000)
        return {"ok": True}

    def uncheck(self, selector):
        self._ensure()
        self.page.locator(str(selector)).first.uncheck(timeout=12000)
        return {"ok": True}

    def press(self, selector, key):
        self._ensure()
        self.page.locator(str(selector)).first.press(str(key), timeout=12000)
        return {"ok": True}

    def scroll(self, y=700):
        self._ensure()
        self.page.mouse.wheel(0, int(y))
        return {"ok": True}

    def wait_text(self, text, timeout_ms=15000):
        self._ensure()
        self.page.get_by_text(str(text)).first.wait_for(state="visible", timeout=int(timeout_ms))
        return {"ok": True}

    def wait_selector(self, selector, timeout_ms=15000):
        self._ensure()
        self.page.locator(str(selector)).first.wait_for(state="visible", timeout=int(timeout_ms))
        return {"ok": True}

    def wait_url(self, pattern, timeout_ms=20000):
        self._ensure()
        self.page.wait_for_url(str(pattern), timeout=int(timeout_ms))
        return {"ok": True, "url": self.page.url}

    def exists(self, selector):
        self._ensure()
        count = self.page.locator(str(selector)).count()
        return {"ok": True, "exists": count > 0, "count": count}

    def count(self, selector):
        self._ensure()
        return {"ok": True, "count": self.page.locator(str(selector)).count()}

    def text_of(self, selector, max_chars=5000):
        self._ensure()
        txt = self.page.locator(str(selector)).first.inner_text(timeout=10000)
        return {"ok": True, "text": txt[:int(max_chars)]}

    def attribute(self, selector, name):
        self._ensure()
        value = self.page.locator(str(selector)).first.get_attribute(str(name), timeout=10000)
        return {"ok": True, "value": value}

    def screenshot(self, filename="browser.png", full_page=False):
        self._ensure()
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(filename))
        path = self.downloads_dir / safe
        self.page.screenshot(path=str(path), full_page=bool(full_page))
        return {"ok": True, "path": str(path)}

    def download_click(self, text, filename=None):
        self._ensure()
        with self.page.expect_download(timeout=30000) as info:
            self.page.get_by_text(str(text)).first.click()
        download = info.value
        suggested = filename or download.suggested_filename
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(suggested))
        path = self.downloads_dir / safe
        download.save_as(str(path))
        return {"ok": True, "path": str(path), "suggested_filename": download.suggested_filename}

    def upload_file(self, selector, path):
        self._ensure()
        p = Path(path).expanduser().resolve()
        if not p.is_file():
            return {"ok": False, "error": "Arquivo não encontrado."}
        self.page.locator(str(selector)).first.set_input_files(str(p))
        return {"ok": True, "path": str(p)}


    def search_google(self, query, limit=10):
        self._ensure()
        q = str(query).strip()
        url = "https://www.google.com/search?q=" + __import__("urllib.parse").parse.quote_plus(q)
        self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
        try:
            self.page.wait_for_timeout(900)
        except Exception:
            pass
        items = self.page.evaluate(
            """() => Array.from(document.querySelectorAll('a')).map(a => {
                const h = a.querySelector('h3');
                if (!h) return null;
                return {title:(h.innerText||'').trim(), url:a.href||'', snippet:''};
            }).filter(Boolean)
              .filter(x => x.title && /^https?:/.test(x.url) && !x.url.includes('google.com/search'))
            """
        )
        out=[]
        seen=set()
        for item in items or []:
            u=item.get('url','')
            if not u or u in seen:
                continue
            seen.add(u)
            out.append(item)
            if len(out) >= int(limit):
                break
        return {"ok": True, "query": q, "items": out, "count": len(out), "provider": "Google via Browser Agent", "url": self.page.url}

    def inspect_page(self, url=None, wait_ms=1400, max_chars=14000):
        """Open a page and collect visible text/structure without asking the LLM to navigate."""
        self._ensure()
        if url:
            target=str(url).strip()
            if not re.match(r"^https?://", target, re.I):
                target="https://"+target
            self.page.goto(target, wait_until="domcontentloaded", timeout=30000)
        try:
            self.page.wait_for_timeout(int(wait_ms))
        except Exception:
            pass
        try:
            text=self.page.locator("body").inner_text(timeout=10000)
        except Exception:
            text=""
        try:
            headings=self.page.locator("h1,h2,h3,h4").evaluate_all(
                """els => els.map(e => ({level:e.tagName,text:(e.innerText||'').trim()})).filter(x=>x.text)"""
            )
        except Exception:
            headings=[]
        try:
            tables=self.page.locator("table").evaluate_all(
                """els => els.map(t => ({rows:t.rows.length,preview:(t.innerText||'').trim().slice(0,2200)}))"""
            )
        except Exception:
            tables=[]
        return {
            "ok": True,
            "url": self.page.url,
            "title": self._safe_title(),
            "text": text[:int(max_chars)],
            "headings": headings[:50],
            "tables": tables[:20],
        }

    def session_summary(self):
        self._ensure()
        return {
            "ok": True,
            "pages": self.pages(),
            "current": {
                "url": self.page.url,
                "title": self._safe_title(),
            },
            "profile_dir": str(self.profile_dir),
        }
