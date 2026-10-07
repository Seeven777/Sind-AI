from __future__ import annotations

import html
import ipaddress
import json
import re
import socket
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

from .base import RiskLevel, ToolResult


_UA = "JarvisNext/1.0 (+local personal agent)"


class _DDGParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.results=[]
        self._in_link=False
        self._href=None
        self._text=[]

    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        classes=attrs.get("class","")
        if tag=="a" and "result__a" in classes:
            self._in_link=True
            self._href=attrs.get("href")
            self._text=[]

    def handle_data(self,data):
        if self._in_link:
            self._text.append(data)

    def handle_endtag(self,tag):
        if tag=="a" and self._in_link:
            title=html.unescape("".join(self._text)).strip()
            href=self._href or ""
            parsed=urllib.parse.urlparse(href)
            query=urllib.parse.parse_qs(parsed.query)
            if query.get("uddg"):
                href=query["uddg"][0]
            if title and href:
                self.results.append({"title":title,"url":href})
            self._in_link=False
            self._href=None
            self._text=[]


class _BingParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.results=[]
        self._algo_depth=0
        self._capture=False
        self._href=''
        self._text=[]

    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        classes=str(attrs.get("class", "")).split()
        if tag=="li" and "b_algo" in classes:
            self._algo_depth=1
            return
        if self._algo_depth:
            if tag=="li": self._algo_depth+=1
            if tag=="a" and not self._capture:
                href=str(attrs.get("href") or "")
                if href.startswith(("http://","https://")):
                    self._capture=True;self._href=href;self._text=[]

    def handle_data(self,data):
        if self._capture:self._text.append(data)

    def handle_endtag(self,tag):
        if tag=="a" and self._capture:
            title=html.unescape("".join(self._text)).strip()
            if title and self._href:
                self.results.append({"title":title,"url":self._href})
            self._capture=False;self._href='';self._text=[]
        if tag=="li" and self._algo_depth:
            self._algo_depth-=1


def _bing_rss_results(body,limit):
    try:
        root=ET.fromstring(body)
    except ET.ParseError:
        return []
    out=[]
    for item in root.findall('.//item'):
        title=(item.findtext('title') or '').strip()
        link=(item.findtext('link') or '').strip()
        if title and link.startswith(('http://','https://')):
            out.append({'title':title,'url':link})
        if len(out)>=limit:break
    return out


class _TextParser(HTMLParser):
    SKIP={"script","style","noscript","svg"}
    def __init__(self):
        super().__init__()
        self.parts=[]
        self.depth=0
        self.title=[]
        self._in_title=False

    def handle_starttag(self,tag,attrs):
        if tag in self.SKIP:
            self.depth+=1
        if tag=="title":
            self._in_title=True

    def handle_endtag(self,tag):
        if tag in self.SKIP and self.depth:
            self.depth-=1
        if tag=="title":
            self._in_title=False
        if tag in {"p","div","li","br","h1","h2","h3","article","section"} and not self.depth:
            self.parts.append("\n")

    def handle_data(self,data):
        if self.depth:
            return
        value=html.unescape(data)
        if self._in_title:
            self.title.append(value)
        self.parts.append(value)

    def text(self):
        value=" ".join(self.parts)
        value=re.sub(r"[ \t]+"," ",value)
        value=re.sub(r"\n\s*\n+","\n\n",value)
        return value.strip()


def _public_host(hostname:str)->bool:
    try:
        infos=socket.getaddrinfo(hostname,None)
    except OSError:
        return False
    for info in infos:
        raw=info[4][0]
        try:
            ip=ipaddress.ip_address(raw)
        except ValueError:
            return False
        if (
            ip.is_private or ip.is_loopback or ip.is_link_local or
            ip.is_multicast or ip.is_reserved or ip.is_unspecified
        ):
            return False
    return True


class WebSearchTool:
    tool_id="web.search"
    risk=RiskLevel.READ

    def __init__(self,timeout=20,max_results=8):
        self.timeout=timeout
        self.max_results=max_results

    def _request_html(self,url):
        req=urllib.request.Request(url,headers={
            "User-Agent":_UA,
            "Accept":"text/html,application/xhtml+xml",
        })
        with urllib.request.urlopen(req,timeout=self.timeout) as response:
            return response.read(2_000_000).decode("utf-8","replace")

    def execute(self,payload):
        query=str(payload.get("query") or "").strip()
        if not query:
            return ToolResult(False,error="query obrigatório")
        limit=max(1,min(int(payload.get("limit",self.max_results)),10))
        ddg_url="https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q":query})
        results=[];engine='duckduckgo_html';request_url=ddg_url;last_error=None
        try:
            body=self._request_html(ddg_url)
            parser=_DDGParser();parser.feed(body);results=parser.results[:limit]
        except Exception as exc:
            last_error=exc

        # Bing RSS is intentionally the first fallback: unlike fragile HTML
        # selectors it exposes a small, structured public result feed and does
        # not require an API key.
        if not results:
            bing_rss='https://www.bing.com/search?' + urllib.parse.urlencode({
                'q':query,'format':'rss','setlang':'pt-BR'
            })
            try:
                body=self._request_html(bing_rss)
                results=_bing_rss_results(body,limit)
                if results:
                    engine='bing_rss';request_url=bing_rss;last_error=None
            except Exception as exc:
                last_error=exc

        if not results:
            bing_url='https://www.bing.com/search?' + urllib.parse.urlencode({'q':query,'setlang':'pt-BR'})
            try:
                body=self._request_html(bing_url)
                parser=_BingParser();parser.feed(body);results=parser.results[:limit]
                if results:
                    engine='bing_html';request_url=bing_url;last_error=None
            except Exception as exc:
                last_error=exc
        if results:
            return ToolResult(True,{"query":query,"results":results,"count":len(results)},
                               {"engine":engine,"request_url":request_url,"results":len(results)},None)
        return ToolResult(False,{"query":query,"results":[],"count":0},
                          {"engine":engine,"request_url":request_url,"results":0},
                          'Nenhum resultado encontrado.' if last_error is None else f'Falha na pesquisa web: {last_error}')

    def verify(self,payload,result):
        ok=bool(result.success and result.output.get("results"))
        return ToolResult(ok,result.output,result.evidence,result.error if not ok else None)


class WebFetchTool:
    tool_id="web.fetch"
    risk=RiskLevel.READ

    def __init__(self,timeout=20,max_bytes=2_000_000,max_chars=18_000):
        self.timeout=timeout
        self.max_bytes=max_bytes
        self.max_chars=max_chars

    def execute(self,payload):
        url=str(payload.get("url") or "").strip()
        try:
            parsed=urllib.parse.urlparse(url)
        except Exception:
            return ToolResult(False,error="URL inválida.")
        if parsed.scheme not in {"http","https"} or not parsed.hostname:
            return ToolResult(False,error="Somente URLs http/https são permitidas.")
        if not payload.get("allow_private",False) and not _public_host(parsed.hostname):
            return ToolResult(False,error="Destino privado/local bloqueado pelo WebFetch.")
        req=urllib.request.Request(url,headers={
            "User-Agent":_UA,
            "Accept":"text/html,text/plain,application/json;q=0.9,*/*;q=0.5",
        })
        try:
            with urllib.request.urlopen(req,timeout=self.timeout) as response:
                final_url=response.geturl()
                content_type=response.headers.get("Content-Type","")
                body=response.read(self.max_bytes)
        except Exception as exc:
            return ToolResult(False,error=f"Falha ao acessar URL: {exc}")

        text=body.decode("utf-8","replace")
        title=""
        if "html" in content_type.lower() or "<html" in text[:1000].lower():
            parser=_TextParser()
            parser.feed(text)
            title=" ".join(parser.title).strip()
            text=parser.text()
        text=text[:self.max_chars]
        return ToolResult(
            True,
            {"url":final_url,"title":title,"content":text,"content_type":content_type},
            {"url":final_url,"bytes":len(body),"chars":len(text),"http_read":True},
        )

    def verify(self,payload,result):
        ok=bool(result.success and result.evidence.get("http_read") and result.output.get("url"))
        return ToolResult(ok,result.output,result.evidence,result.error if not ok else None)
