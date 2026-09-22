import ipaddress
import json
import re
import socket
import time
import urllib.parse
from pathlib import Path

import requests
from bs4 import BeautifulSoup

class PublicDataEngine:
    """Broker de dados públicos. Mantém catálogo/limites fora do contexto do LLM."""
    def __init__(self, registry_path, proposal_path=None, user_agent="JarvisLocal/1.0"):
        self.registry_path=Path(registry_path)
        self.proposal_path=Path(proposal_path) if proposal_path else None
        if self.proposal_path:self.proposal_path.parent.mkdir(parents=True,exist_ok=True)
        self.user_agent=user_agent
        self.session=requests.Session();self.session.headers.update({"User-Agent":user_agent,"Accept":"application/json,text/plain,*/*"})
        self._last_request={};self.reload()
    def reload(self):
        data=json.loads(self.registry_path.read_text(encoding="utf-8"));self.sources=data.get("sources",[]);self.by_id={x["id"]:x for x in self.sources}
    def stats(self):
        return {"ok":True,"sources":len(self.sources),"official":sum(1 for x in self.sources if x.get("authority")=="official"),"countries":sorted(set(x.get("country","") for x in self.sources))}
    def list_sources(self,authority=None,country=None,limit=100):
        items=self.sources
        if authority:items=[x for x in items if x.get("authority")==authority]
        if country:items=[x for x in items if x.get("country","").lower()==str(country).lower()]
        return {"ok":True,"items":items[:int(limit)],"count":len(items)}
    def get_source(self,source_id):
        item=self.by_id.get(str(source_id));return {"ok":bool(item),"data":item,"error":None if item else "Fonte não encontrada."}
    def _normalize(self,text):
        import unicodedata
        s=unicodedata.normalize("NFKD",str(text or "").lower());return "".join(ch for ch in s if not unicodedata.combining(ch))
    def recommend(self,query,limit=8):
        q=self._normalize(query)
        tokens=[x for x in re.findall(r"[a-z0-9_-]{3,}",q) if x not in {"para","sobre","como","dados","publicos","publico","quero","preciso","informacao","informacoes"}]
        synonym={
          "trabalho":["emprego","rais","caged","trabalhistas"],"emprego":["trabalho","rais","caged"],
          "lei":["legislacao","projetos","materias","judiciais"],"processo":["judiciais","tribunais","datajud"],
          "empresa":["cnpj","cadastro"],"municipio":["ibge","localidades","geografia"],
          "cientifico":["artigos","doi","pesquisa"],"artigo":["artigos","doi","publicacoes"],
          "mapa":["mapas","lugares","geodados"],"noticia":["noticias","midia"],
          "juros":["selic","credito","bcb"],"cambio":["bcb","economia"],"licitacao":["compras","pncp","contratos"]
        }
        expanded=list(tokens)
        for t in tokens:expanded+=synonym.get(t,[])
        authority_bonus={"official":6,"official_international":5,"primary_metadata":4,"platform":2,"community":1}
        ranked=[]
        for source in self.sources:
            hay=self._normalize(" ".join([source.get("id",""),source.get("name",""),source.get("authority","")," ".join(source.get("topics",[])),source.get("notes","")]))
            matched=sum(1 for t in expanded if t and t in hay);score=authority_bonus.get(source.get("authority"),1)+matched*4
            if q and q in hay:score+=8
            if matched or (q and q in hay):ranked.append((score,source))
        ranked.sort(key=lambda x:(-x[0],x[1]["name"]))
        return {"ok":True,"query":query,"items":[x[1] for x in ranked[:int(limit)]],"count":len(ranked)}
    def _rate(self,key,seconds):
        now=time.monotonic();last=self._last_request.get(key,0);wait=float(seconds)-(now-last)
        if wait>0:time.sleep(wait)
        self._last_request[key]=time.monotonic()
    def _safe_public_https(self,url):
        parsed=urllib.parse.urlsplit(str(url));
        if parsed.scheme!="https" or not parsed.hostname:raise ValueError("Somente URLs HTTPS públicas são aceitas.")
        host=parsed.hostname.lower()
        if host in {"localhost","127.0.0.1","::1"} or host.endswith(".local"):raise ValueError("Endereço local/privado bloqueado.")
        try:
            for info in socket.getaddrinfo(host,None):
                ip=ipaddress.ip_address(info[4][0])
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:raise ValueError("Endereço local/privado bloqueado.")
        except socket.gaierror:pass
        return url
    def _get_json(self,url,params=None,timeout=20,min_interval=.2,key="public"):
        self._safe_public_https(url);self._rate(key,min_interval);r=self.session.get(url,params=params or {},timeout=timeout);r.raise_for_status()
        try:return r.json(),r.url
        except Exception:return {"text":r.text[:30000]},r.url
    def query(self,source_id,operation,params=None):
        source_id=str(source_id);operation=str(operation);params=dict(params or {})
        try:
            mapping={"ibge":self._query_ibge,"camara":self._query_camara,"dados_gov_br":self._query_dados_gov,"dados_abertos_sp":self._query_dados_abertos_sp,"crossref":self._query_crossref,"wikidata":self._query_wikidata,"github":self._query_github,"open_meteo":self._query_open_meteo,"nominatim":self._query_nominatim,"overpass":self._query_overpass,"brasilapi":self._query_brasilapi,"datajud":self._query_datajud,"senado":self._query_senado}
            if source_id in mapping:return mapping[source_id](operation,params)
            if source_id in {"receita_federal","mte_pdet"}:return self._catalog_links(source_id,operation,params)
            if source_id=="inep":return self._inep_catalog(operation,params)
            source=self.by_id.get(source_id)
            if source and operation=="discover_interfaces":
                homepage=source.get("homepage")
                if not homepage:return {"ok":False,"error":"Fonte sem homepage registrada.","source":source_id}
                result=self.discover_interfaces(homepage,save=True);result["source"]=source_id;return result
            return {"ok":False,"error":f"Fonte não possui adaptador direto para '{operation}'.","source":source_id,"available_operations":(source or {}).get("operations",[])}
        except Exception as exc:return {"ok":False,"error":str(exc),"source":source_id,"operation":operation}
    def _query_ibge(self,op,p):
        if op=="states":url="https://servicodados.ibge.gov.br/api/v1/localidades/estados";data,final=self._get_json(url,{"orderBy":p.get("orderBy","nome")},key="ibge")
        elif op=="municipalities":
            uf=str(p.get("uf","")).strip();url=f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{urllib.parse.quote(uf)}/municipios" if uf else "https://servicodados.ibge.gov.br/api/v1/localidades/municipios";data,final=self._get_json(url,{"orderBy":p.get("orderBy","nome")},key="ibge")
        elif op=="aggregates":url="https://servicodados.ibge.gov.br/api/v3/agregados";data,final=self._get_json(url,{k:v for k,v in p.items() if k in {"periodo","assunto","classificacao","periodicidade","nivel"} and v not in (None,"")},key="ibge")
        elif op=="aggregate_metadata":
            ag=urllib.parse.quote(str(p["agregado"]));data,final=self._get_json(f"https://servicodados.ibge.gov.br/api/v3/agregados/{ag}/metadados",key="ibge")
        elif op=="aggregate_values":
            ag=urllib.parse.quote(str(p["agregado"]));var=urllib.parse.quote(str(p["variavel"]));periods=urllib.parse.quote(str(p.get("periodos","-6")),safe="-|/")
            url=f"https://servicodados.ibge.gov.br/api/v3/agregados/{ag}/periodos/{periods}/variaveis/{var}";data,final=self._get_json(url,{k:v for k,v in p.items() if k in {"localidades","classificacao","view"} and v not in (None,"")},key="ibge")
        else:return {"ok":False,"error":"Operações IBGE: states, municipalities, aggregates, aggregate_metadata, aggregate_values."}
        return {"ok":True,"source":"ibge","operation":op,"url":final,"data":data}
    def _query_camara(self,op,p):
        path={"propositions":"proposicoes","deputies":"deputados","events":"eventos","organs":"orgaos"}.get(op)
        if op=="get":path=str(p.get("path","")).strip().lstrip("/")
        if not path or ".." in path:return {"ok":False,"error":"Operações Câmara: propositions, deputies, events, organs, get."}
        data,final=self._get_json("https://dadosabertos.camara.leg.br/api/v2/"+path,p.get("params",{}) if op=="get" else {k:v for k,v in p.items() if k!="path" and v not in (None,"")},key="camara")
        return {"ok":True,"source":"camara","operation":op,"url":final,"data":data}
    def _query_dados_gov(self,op,p):
        base="https://dados.gov.br/dados/api/publico/"
        if op=="datasets":path="conjuntos-dados";q={"pagina":int(p.get("page",1)),"quantidade":min(50,int(p.get("limit",10)))};q.update({k:v for k,v in p.items() if k in {"titulo","organizacao","tag","tema"} and v})
        elif op=="dataset":path="conjuntos-dados/"+urllib.parse.quote(str(p["id"]));q={}
        elif op in {"organizations","themes","tags"}:path={"organizations":"organizacoes","themes":"temas","tags":"tags"}[op];q={}
        else:return {"ok":False,"error":"Operações Dados.gov: datasets, dataset, organizations, themes, tags."}
        data,final=self._get_json(base+path,q,key="dados_gov");return {"ok":True,"source":"dados_gov_br","operation":op,"url":final,"data":data}
    def _query_dados_abertos_sp(self,op,p):
        base="https://dadosabertos.sp.gov.br/api/3/action/"
        if op=="datasets":
            action="package_search";q={"q":p.get("query",p.get("q","")),"rows":min(100,int(p.get("limit",10))),"start":max(0,int(p.get("start",0)))}
        elif op=="dataset":
            action="package_show";q={"id":str(p.get("id",p.get("name","")))}
        elif op=="organizations":
            action="organization_list";q={"all_fields":"true","limit":min(1000,int(p.get("limit",100)))}
        elif op=="groups":
            action="group_list";q={"all_fields":"true","limit":min(1000,int(p.get("limit",100)))}
        elif op=="tags":
            action="tag_list";q={"all_fields":"true"}
        else:
            return {"ok":False,"error":"Operações Dados Abertos SP: datasets, dataset, organizations, groups, tags."}
        data,final=self._get_json(base+action,q,key="dados_abertos_sp")
        return {"ok":True,"source":"dados_abertos_sp","operation":op,"url":final,"data":data}

    def _query_crossref(self,op,p):
        if op!="works":return {"ok":False,"error":"Operação Crossref: works."}
        q={"query":p.get("query",p.get("q","")),"rows":min(20,int(p.get("rows",p.get("limit",5))))};data,final=self._get_json("https://api.crossref.org/works",q,min_interval=.2,key="crossref");return {"ok":True,"source":"crossref","operation":op,"url":final,"data":data}
    def _query_wikidata(self,op,p):
        if op!="sparql":return {"ok":False,"error":"Operação Wikidata: sparql."}
        query=str(p.get("query","")).strip()
        if not query or len(query)>10000:return {"ok":False,"error":"SPARQL vazio ou grande demais."}
        data,final=self._get_json("https://query.wikidata.org/sparql",{"query":query,"format":"json"},min_interval=.5,key="wikidata");return {"ok":True,"source":"wikidata","operation":op,"url":final,"data":data}
    def _query_github(self,op,p):
        old=self.session.headers.copy();self.session.headers.update({"Accept":"application/vnd.github+json","User-Agent":self.user_agent})
        try:
            if op=="search_repositories":data,final=self._get_json("https://api.github.com/search/repositories",{"q":p.get("query",""),"per_page":min(30,int(p.get("limit",10)))},min_interval=.4,key="github")
            elif op=="repo":data,final=self._get_json(f"https://api.github.com/repos/{urllib.parse.quote(str(p['owner']))}/{urllib.parse.quote(str(p['repo']))}",min_interval=.4,key="github")
            else:return {"ok":False,"error":"Operações GitHub: search_repositories, repo."}
        finally:self.session.headers.clear();self.session.headers.update(old)
        return {"ok":True,"source":"github","operation":op,"url":final,"data":data}
    def _query_open_meteo(self,op,p):
        if op!="forecast":return {"ok":False,"error":"Operação Open-Meteo: forecast."}
        q={"latitude":p["latitude"],"longitude":p["longitude"],"timezone":p.get("timezone","auto")}
        for k in ("current","hourly","daily","forecast_days"):
            if p.get(k) not in (None,""):q[k]=p[k]
        data,final=self._get_json("https://api.open-meteo.com/v1/forecast",q,key="open_meteo");return {"ok":True,"source":"open_meteo","operation":op,"url":final,"data":data}
    def _query_nominatim(self,op,p):
        if op!="search":return {"ok":False,"error":"Operação Nominatim: search."}
        data,final=self._get_json("https://nominatim.openstreetmap.org/search",{"q":p.get("query",""),"format":"jsonv2","limit":min(10,int(p.get("limit",5))),"addressdetails":1},min_interval=1.05,key="nominatim");return {"ok":True,"source":"nominatim","operation":op,"url":final,"data":data}
    def _query_overpass(self,op,p):
        if op!="query":return {"ok":False,"error":"Operação Overpass: query."}
        query=str(p.get("query","")).strip()
        if not query or len(query)>12000:return {"ok":False,"error":"Consulta Overpass vazia ou grande demais."}
        self._rate("overpass",2);r=self.session.post("https://overpass-api.de/api/interpreter",data={"data":query},timeout=min(45,int(p.get("timeout",30))));r.raise_for_status()
        try:data=r.json()
        except Exception:data={"text":r.text[:30000]}
        return {"ok":True,"source":"overpass","operation":op,"url":r.url,"data":data}
    def _query_brasilapi(self,op,p):
        if op=="cep":path="cep/v2/"+re.sub(r"\D","",str(p["cep"]))
        elif op=="cnpj":path="cnpj/v1/"+re.sub(r"\D","",str(p["cnpj"]))
        elif op=="banks":path="banks/v1"
        else:return {"ok":False,"error":"Operações BrasilAPI: cep, cnpj, banks."}
        data,final=self._get_json("https://brasilapi.com.br/api/"+path,min_interval=.4,key="brasilapi");return {"ok":True,"source":"brasilapi","operation":op,"url":final,"data":data}
    def _datajud_key(self):
        self._rate("datajud_key",10);r=self.session.get("https://datajud-wiki.cnj.jus.br/api-publica/acesso/",timeout=15);r.raise_for_status();text=BeautifulSoup(r.text,"html.parser").get_text(" ",strip=True);m=re.search(r"Authorization:\s*APIKey\s+([A-Za-z0-9_\-=]+)",text,re.I)
        if not m:raise RuntimeError("Não foi possível obter a chave pública vigente do DataJud.")
        return m.group(1)
    def _query_datajud(self,op,p):
        if op!="search":return {"ok":False,"error":"Operação DataJud: search."}
        alias=re.sub(r"[^a-z0-9_]","",str(p.get("tribunal_alias","")).lower());alias=alias if alias.startswith("api_publica_") else "api_publica_"+alias
        body=p.get("body") or {"size":min(10,int(p.get("size",10))),"query":{"match_all":{}}};key=self._datajud_key();url=f"https://api-publica.datajud.cnj.jus.br/{alias}/_search";self._rate("datajud",.5)
        r=self.session.post(url,json=body,headers={"Authorization":"APIKey "+key,"Content-Type":"application/json","User-Agent":self.user_agent},timeout=30);r.raise_for_status();return {"ok":True,"source":"datajud","operation":op,"url":url,"data":r.json()}
    def _query_senado(self,op,p):
        if op!="get":return {"ok":False,"error":"Operação Senado: get."}
        path=str(p.get("path","")).strip().lstrip("/")
        if ".." in path:raise ValueError("Path inválido.")
        data,final=self._get_json("https://legis.senado.leg.br/dadosabertos/"+path,p.get("params",{}),key="senado");return {"ok":True,"source":"senado","operation":op,"url":final,"data":data}
    def _catalog_links(self,source_id,op,p):
        if op not in {"links","catalog"}:return {"ok":False,"error":"Fonte bulk suporta links/catalog."}
        url="https://www.gov.br/receitafederal/dados" if source_id=="receita_federal" else "https://www.gov.br/trabalho-e-emprego/pt-br/acesso-a-informacao/acoes-e-programas/programas-projetos-acoes-obras-e-atividades/estatisticas-trabalho/microdados-rais-e-caged"
        return self._scrape_catalog(source_id,url,p)
    def _inep_catalog(self,op,p):
        if op!="catalog":return {"ok":False,"error":"Operação INEP: catalog."}
        return self._scrape_catalog("inep","https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados",p)
    def _scrape_catalog(self,source_id,url,p):
        self._rate(source_id,1);r=self.session.get(url,timeout=20);r.raise_for_status();soup=BeautifulSoup(r.text,"html.parser");terms=[self._normalize(x) for x in re.findall(r"[A-Za-zÀ-ÿ0-9_-]{3,}",str(p.get("query","")))];items=[];seen=set()
        for a in soup.find_all("a",href=True):
            title=a.get_text(" ",strip=True);href=urllib.parse.urljoin(r.url,a["href"]);hay=self._normalize(title+" "+href)
            if terms and not any(t in hay for t in terms):continue
            if href.startswith(("https://","ftp://")) and href not in seen:seen.add(href);items.append({"title":title or href,"url":href})
            if len(items)>=int(p.get("limit",80)):break
        return {"ok":True,"source":source_id,"operation":"catalog","url":r.url,"items":items,"count":len(items)}
    def discover_interfaces(self,url,save=True):
        try:
            url=self._safe_public_https(str(url).strip());r=self.session.get(url,timeout=15,allow_redirects=True);r.raise_for_status();base=r.url;soup=BeautifulSoup(r.text,"html.parser") if "html" in (r.headers.get("content-type") or "").lower() else None;candidates=[]
            if soup:
                for link in soup.find_all("link",href=True):
                    typ=(link.get("type") or "").lower();rel=" ".join(link.get("rel") or []).lower()
                    if "rss" in typ or "atom" in typ or "alternate" in rel:candidates.append({"kind":"feed","url":urllib.parse.urljoin(base,link["href"])})
            parsed=urllib.parse.urlsplit(base);origin=f"{parsed.scheme}://{parsed.netloc}"
            for path,kind in [("/openapi.json","openapi"),("/swagger.json","openapi"),("/v3/api-docs","openapi"),("/sitemap.xml","sitemap"),("/robots.txt","robots")]:
                target=origin+path
                try:
                    h=self.session.get(target,timeout=5,stream=True)
                    if h.status_code==200:candidates.append({"kind":kind,"url":target,"content_type":h.headers.get("content-type","")})
                    h.close()
                except Exception:pass
            unique=[];seen=set()
            for c in candidates:
                if c["url"] not in seen:unique.append(c);seen.add(c["url"])
            result={"ok":True,"page":base,"interfaces":unique,"count":len(unique)}
            if save and self.proposal_path:
                existing=[]
                if self.proposal_path.exists():
                    try:existing=json.loads(self.proposal_path.read_text(encoding="utf-8"))
                    except Exception:existing=[]
                existing.append({"created_at":time.time(),**result});self.proposal_path.write_text(json.dumps(existing[-200:],indent=2,ensure_ascii=False),encoding="utf-8")
            return result
        except Exception as exc:return {"ok":False,"error":str(exc),"url":str(url)}
    def proposals(self,limit=50):
        if not self.proposal_path or not self.proposal_path.exists():return {"ok":True,"items":[],"count":0}
        try:data=json.loads(self.proposal_path.read_text(encoding="utf-8"))
        except Exception:data=[]
        items=list(reversed(data[-int(limit):]));return {"ok":True,"items":items,"count":len(items)}
    def execute(self,operation,**params):
        mapping={"stats":lambda **_:self.stats(),"list":lambda **kw:self.list_sources(**kw),"source":lambda **kw:self.get_source(kw.get("source_id")),"recommend":lambda **kw:self.recommend(kw.get("query",""),kw.get("limit",8)),"query":lambda **kw:self.query(kw.get("source_id"),kw.get("source_operation"),kw.get("params",{})),"discover":lambda **kw:self.discover_interfaces(kw.get("url",""),kw.get("save",True)),"proposals":lambda **kw:self.proposals(kw.get("limit",50))}
        fn=mapping.get(operation);return fn(**params) if fn else {"ok":False,"error":f"Operação PublicData desconhecida: {operation}"}
