import re
import urllib.parse
import requests
from bs4 import BeautifulSoup
from research.source_resolver import normalize_url


class PublicWebSearch:
    """
    Pesquisa pública gratuita com fallback entre múltiplas interfaces HTML.
    Nenhuma chave, conta ou assinatura é necessária.

    Ordem padrão:
      DuckDuckGo HTML -> DuckDuckGo Lite -> Bing HTML -> Google HTML
      -> Browser Agent (Google) quando disponível.
    """

    def __init__(self, user_agent="JarvisSindPet/0.7.3", browser_fallback=None):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": user_agent,
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.7",
        })
        self.browser_fallback = browser_fallback

    def _decode_ddg_href(self, href):
        if not href:
            return ""
        full = urllib.parse.urljoin("https://duckduckgo.com", href)
        parsed = urllib.parse.urlsplit(full)
        q = dict(urllib.parse.parse_qsl(parsed.query))
        if "uddg" in q:
            return urllib.parse.unquote(q["uddg"])
        return full

    def _clean(self, items, limit):
        out=[]
        seen=set()
        for item in items:
            title=re.sub(r"\s+", " ", str(item.get("title", ""))).strip()
            url=normalize_url(str(item.get("url", "")).strip())
            snippet=re.sub(r"\s+", " ", str(item.get("snippet", ""))).strip()
            if not title or not url.startswith(("http://", "https://")):
                continue
            if url in seen:
                continue
            seen.add(url)
            out.append({"title":title,"url":url,"snippet":snippet})
            if len(out)>=int(limit):
                break
        return out

    def _ddg_html(self, q, limit):
        r=self.session.get("https://html.duckduckgo.com/html/", params={"q":q}, timeout=12)
        r.raise_for_status()
        soup=BeautifulSoup(r.text,"html.parser")
        items=[]
        for result in soup.select(".result"):
            a=result.select_one(".result__a")
            if not a:
                continue
            sn=result.select_one(".result__snippet")
            items.append({
                "title":a.get_text(" ",strip=True),
                "url":self._decode_ddg_href(a.get("href")),
                "snippet":sn.get_text(" ",strip=True) if sn else "",
            })
        return self._clean(items,limit)

    def _ddg_lite(self, q, limit):
        r=self.session.get("https://lite.duckduckgo.com/lite/", params={"q":q}, timeout=12)
        r.raise_for_status()
        soup=BeautifulSoup(r.text,"html.parser")
        items=[]
        for a in soup.select("a.result-link, a[href]"):
            title=a.get_text(" ",strip=True)
            href=self._decode_ddg_href(a.get("href"))
            if title and href.startswith(("http://","https://")) and "duckduckgo.com" not in urllib.parse.urlsplit(href).netloc:
                items.append({"title":title,"url":href,"snippet":""})
        return self._clean(items,limit)

    def _bing(self, q, limit):
        r=self.session.get("https://www.bing.com/search", params={"q":q,"setlang":"pt-br"}, timeout=12)
        r.raise_for_status()
        soup=BeautifulSoup(r.text,"html.parser")
        items=[]
        for li in soup.select("li.b_algo"):
            a=li.select_one("h2 a")
            if not a:
                continue
            sn=li.select_one(".b_caption p")
            items.append({"title":a.get_text(" ",strip=True),"url":a.get("href", ""),"snippet":sn.get_text(" ",strip=True) if sn else ""})
        return self._clean(items,limit)

    def _google_html(self, q, limit):
        r=self.session.get("https://www.google.com/search", params={"q":q,"num":max(10,int(limit)),"hl":"pt-BR"}, timeout=12)
        r.raise_for_status()
        soup=BeautifulSoup(r.text,"html.parser")
        items=[]
        for a in soup.select("a"):
            h=a.find("h3")
            if not h:
                continue
            href=a.get("href","")
            if href.startswith("/url?"):
                params=dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(href).query))
                href=params.get("q") or params.get("url") or ""
            if href.startswith(("http://","https://")):
                items.append({"title":h.get_text(" ",strip=True),"url":href,"snippet":""})
        return self._clean(items,limit)

    def search(self, query, limit=8):
        q=str(query).strip()
        attempts=[]
        providers=[
            ("DuckDuckGo HTML", self._ddg_html),
            ("DuckDuckGo Lite", self._ddg_lite),
            ("Bing HTML", self._bing),
            ("Google HTML", self._google_html),
        ]
        for name,fn in providers:
            try:
                items=fn(q,limit)
                attempts.append({"provider":name,"count":len(items),"ok":True})
                if items:
                    return {"ok":True,"query":q,"items":items,"count":len(items),"provider":name,"attempts":attempts}
            except Exception as exc:
                attempts.append({"provider":name,"count":0,"ok":False,"error":str(exc)[:220]})

        if self.browser_fallback is not None:
            try:
                result=self.browser_fallback.search_google(q,limit=limit)
                attempts.append({"provider":"Google via Browser Agent","count":result.get("count",0),"ok":bool(result.get("ok"))})
                if result.get("ok") and result.get("items"):
                    result["attempts"]=attempts
                    return result
            except Exception as exc:
                attempts.append({"provider":"Google via Browser Agent","count":0,"ok":False,"error":str(exc)[:220]})

        return {"ok":False,"query":q,"items":[],"count":0,"provider":None,"attempts":attempts,"error":"Nenhum provedor gratuito retornou resultados."}

    def execute(self, operation, **params):
        if operation == "search":
            return self.search(params.get("query", ""), params.get("limit", 8))
        if operation == "search_site":
            query=f"site:{params.get('domain','')} {params.get('query','')}".strip()
            return self.search(query,params.get("limit",8))
        if operation == "search_exact":
            query='"'+str(params.get("query","")).strip().replace('"','')+'"'
            return self.search(query,params.get("limit",8))
        if operation == "search_recent":
            period=str(params.get("period","week"))
            query=f"{params.get('query','')} {period}".strip()
            return self.search(query,params.get("limit",8))
        return {"ok":False,"error":f"Operação de busca desconhecida: {operation}"}
