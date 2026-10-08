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


_WEATHER_CODES = {
    0: "céu limpo", 1: "predominantemente limpo", 2: "parcialmente nublado", 3: "nublado",
    45: "neblina", 48: "neblina com geada", 51: "garoa fraca", 53: "garoa moderada",
    55: "garoa intensa", 56: "garoa congelante fraca", 57: "garoa congelante intensa",
    61: "chuva fraca", 63: "chuva moderada", 65: "chuva forte", 66: "chuva congelante fraca",
    67: "chuva congelante forte", 71: "neve fraca", 73: "neve moderada", 75: "neve forte",
    77: "grãos de neve", 80: "pancadas de chuva fracas", 81: "pancadas de chuva moderadas",
    82: "pancadas de chuva fortes", 85: "pancadas de neve fracas", 86: "pancadas de neve fortes",
    95: "trovoadas", 96: "trovoadas com granizo fraco", 99: "trovoadas com granizo forte",
}


class WeatherForecastTool:
    """Structured current/today weather via Open-Meteo (no API key required).

    This is intentionally a read-only first-class tool instead of asking the LLM
    to infer live weather from generic web snippets. The UI can therefore render
    a reliable weather surface even when a search engine changes its HTML.
    """
    tool_id="weather.forecast"
    risk=RiskLevel.READ

    def __init__(self,timeout=12):
        self.timeout=timeout

    def _json(self,url):
        req=urllib.request.Request(url,headers={
            "User-Agent":_UA,
            "Accept":"application/json",
        })
        with urllib.request.urlopen(req,timeout=self.timeout) as response:
            body=response.read(1_000_000).decode("utf-8","replace")
        return json.loads(body)

    def _hourly(self,data,current_time):
        hourly=data.get("hourly") or {}
        times=hourly.get("time") or []
        if not times:return []
        start=0
        if current_time:
            for i,t in enumerate(times):
                if str(t)>=str(current_time):start=i;break
        rows=[]
        for i in range(start,min(len(times),start+8)):
            code=(hourly.get("weather_code") or [None]*len(times))[i]
            try:code=int(code)
            except Exception:code=None
            rows.append({
                "time":times[i],
                "temperature":(hourly.get("temperature_2m") or [None]*len(times))[i],
                "precipitation_probability":(hourly.get("precipitation_probability") or [None]*len(times))[i],
                "wind_speed":(hourly.get("wind_speed_10m") or [None]*len(times))[i],
                "weather_code":code,
                "condition":_WEATHER_CODES.get(code,"condição variável"),
            })
        return rows

    def execute(self,payload):
        location=str(payload.get("location") or "").strip()
        if not location:
            return ToolResult(False,error="location obrigatório")
        geo_url="https://geocoding-api.open-meteo.com/v1/search?" + urllib.parse.urlencode({
            "name":location,"count":1,"language":"pt","format":"json",
        })
        try:
            geo=self._json(geo_url)
            rows=geo.get("results") or []
            if not rows:
                return ToolResult(False,error=f"Local não encontrado: {location}")
            place=rows[0]
            lat=float(place["latitude"]);lon=float(place["longitude"])
            forecast_url="https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode({
                "latitude":lat,"longitude":lon,
                "current":"temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,rain,weather_code,wind_speed_10m",
                "hourly":"temperature_2m,precipitation_probability,weather_code,wind_speed_10m",
                "daily":"temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code",
                "timezone":"auto","forecast_days":1,
            })
            data=self._json(forecast_url)
        except Exception as exc:
            return ToolResult(False,error=f"Falha ao consultar previsão: {exc}")
        current=data.get("current") or {}
        daily=data.get("daily") or {}
        units=data.get("current_units") or {}
        daily_units=data.get("daily_units") or {}
        code=current.get("weather_code")
        try: code=int(code)
        except Exception: code=None
        def first(key):
            value=daily.get(key)
            return value[0] if isinstance(value,list) and value else None
        place_name=str(place.get("name") or location)
        admin=str(place.get("admin1") or "").strip()
        country=str(place.get("country") or "").strip()
        full=", ".join(x for x in (place_name,admin,country) if x)
        out={
            "location":full or location,
            "latitude":lat,"longitude":lon,"timezone":data.get("timezone"),
            "current":{
                "temperature":current.get("temperature_2m"),
                "apparent_temperature":current.get("apparent_temperature"),
                "humidity":current.get("relative_humidity_2m"),
                "precipitation":current.get("precipitation"),
                "rain":current.get("rain"),
                "wind_speed":current.get("wind_speed_10m"),
                "weather_code":code,
                "condition":_WEATHER_CODES.get(code,"condição variável"),
                "time":current.get("time"),
            },
            "today":{
                "temperature_max":first("temperature_2m_max"),
                "temperature_min":first("temperature_2m_min"),
                "precipitation_probability_max":first("precipitation_probability_max"),
                "weather_code":first("weather_code"),
            },
            "hourly":self._hourly(data,current.get("time")),
            "units":{
                "temperature":units.get("temperature_2m","°C"),
                "humidity":units.get("relative_humidity_2m","%"),
                "precipitation":units.get("precipitation","mm"),
                "wind_speed":units.get("wind_speed_10m","km/h"),
                "probability":daily_units.get("precipitation_probability_max","%"),
            },
            "provider":"Open-Meteo",
            "source":"https://open-meteo.com/",
        }
        return ToolResult(True,out,{"provider":"Open-Meteo","geocoded":True,"forecast_read":True})

    def verify(self,payload,result):
        ok=bool(result.success and result.evidence.get("forecast_read") and result.output.get("current"))
        return ToolResult(ok,result.output,result.evidence,result.error if not ok else None)


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
