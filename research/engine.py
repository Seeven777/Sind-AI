import json
import re
from datetime import datetime
from pathlib import Path

from .extractor import SourceExtractor
from .source_resolver import authority_score, domain_of, normalize_url, source_identity


class ResearchEngine:
    def __init__(self, web_search, history_dir=None):
        self.web_search = web_search
        self.extractor = SourceExtractor()
        self.history_dir = Path(history_dir) if history_dir else None
        if self.history_dir:
            self.history_dir.mkdir(parents=True, exist_ok=True)
            self.history_path = self.history_dir / 'research_history.jsonl'
            self.last_path = self.history_dir / 'last_research.json'
        else:
            self.history_path = None
            self.last_path = None

    def _terms(self, query):
        return self.extractor.query_terms(query)

    def query_variants(self, query):
        q = str(query).strip()
        variants = [q]
        low = q.lower()
        if re.search(r'\bnr\s*-?\s*\d+', low):
            variants += [
                f'site:gov.br/trabalho-e-emprego {q}',
                f'site:gov.br {q}',
                f'site:fundacentro.gov.br {q}',
            ]
        elif any(x in low for x in ['trabalho','trabalhador','clt','cct','segurança','saúde ocupacional']):
            variants += [f'site:gov.br {q}', f'site:tst.jus.br {q}', f'site:mpt.mp.br {q}']
        else:
            variants += [f'site:gov.br {q}']
        out=[]
        seen=set()
        for v in variants:
            key=v.lower()
            if key not in seen:
                seen.add(key); out.append(v)
        return out[:4]

    def normalize_result(self, item, query=''):
        url = normalize_url(item.get('url',''))
        identity = source_identity(url, query=query)
        return {
            'title': re.sub(r'\s+',' ',str(item.get('title',''))).strip(),
            'url': url,
            'snippet': re.sub(r'\s+',' ',str(item.get('snippet',''))).strip(),
            'provider': item.get('provider'),
            **identity,
        }

    def _relevance_score(self, item, query):
        terms = self._terms(query)
        hay = f"{item.get('title','')} {item.get('snippet','')} {item.get('url','')}".lower()
        overlap = sum(1 for t in terms if t in hay)
        phrase = 10 if str(query).lower() in hay else 0
        return int(item.get('authority_score',0)) + overlap * 6 + phrase

    def dedupe_results(self, items):
        out=[]; seen=set()
        for item in items:
            key=(item.get('url') or '').lower().rstrip('/')
            if not key or key in seen:
                continue
            seen.add(key); out.append(item)
        return out

    def rank_results(self, items, query):
        normalized=[self.normalize_result(x,query=query) for x in items]
        normalized=self.dedupe_results(normalized)
        for item in normalized:
            item['rank_score']=self._relevance_score(item,query)
        return sorted(normalized,key=lambda x:(-x.get('rank_score',0),x.get('domain','')))

    def search(self, query, limit=10, official_first=True):
        attempts=[]; combined=[]
        all_variants=self.query_variants(query) if official_first else [str(query)]
        # CPU/network budget: normal search + the best official specialization.
        variants=[all_variants[0]]
        if official_first and len(all_variants)>1:
            variants.append(all_variants[1])
        for variant in variants:
            r=self.web_search.search(variant,limit=max(5,int(limit)))
            attempts.append({'query':variant,'ok':r.get('ok'), 'provider':r.get('provider'), 'count':r.get('count',0), 'attempts':r.get('attempts',[])})
            if r.get('ok'):
                for item in r.get('items',[]):
                    row=dict(item); row['provider']=r.get('provider'); combined.append(row)
        ranked=self.rank_results(combined,query)[:int(limit)]
        return {'ok':bool(ranked),'query':str(query),'items':ranked,'count':len(ranked),'attempts':attempts,'variants':variants}

    def fetch_source(self, url, query=''):
        normalized=normalize_url(url)
        result=self.extractor.fetch(normalized)
        identity=source_identity(result.get('url') or normalized, query=query)
        result.update(identity)
        return result

    def evidence_card(self, item, query, sentence_limit=5):
        fetched=self.fetch_source(item.get('url',''),query=query)
        text=fetched.get('text','') if fetched.get('ok') else ''
        sentences=self.extractor.relevant_sentences(text or item.get('snippet',''),query,limit=sentence_limit)
        return {
            'title': fetched.get('title') or item.get('title') or item.get('domain') or 'Fonte',
            'url': fetched.get('url') or item.get('url'),
            'domain': fetched.get('domain') or item.get('domain'),
            'source_type': fetched.get('source_type') or item.get('source_type'),
            'authority_score': fetched.get('authority_score') or item.get('authority_score',0),
            'official': bool(fetched.get('official') or item.get('official')),
            'published': fetched.get('published',''),
            'description': fetched.get('description','') or item.get('snippet',''),
            'sentences': sentences,
            'headings': fetched.get('headings',[])[:12],
            'fetched': bool(fetched.get('ok')),
            'error': fetched.get('error') if not fetched.get('ok') else None,
            'content_kind': fetched.get('content_kind'),
        }

    def evidence_pack(self, query, limit=5, official_first=True):
        search=self.search(query,limit=max(limit+3,8),official_first=official_first)
        if not search.get('items'):
            return {'ok':False,'query':query,'error':'Nenhuma fonte encontrada.','search':search,'cards':[]}
        cards=[]
        # Fetch high-ranked distinct domains first.
        domains=set()
        selected=[]
        for item in search['items']:
            d=item.get('domain')
            if d not in domains or len(selected) < 2:
                selected.append(item); domains.add(d)
            if len(selected)>=int(limit): break
        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=min(4, max(1, len(selected)))) as pool:
            futures=[pool.submit(self.evidence_card,item,query) for item in selected]
            for future in as_completed(futures):
                try: cards.append(future.result())
                except Exception as exc: cards.append({'title':'Fonte','url':'','sentences':[],'fetched':False,'error':str(exc),'authority_score':0})
        cards.sort(key=lambda x:(-int(x.get('authority_score') or 0), not x.get('fetched')))
        return {'ok':True,'query':query,'search':search,'cards':cards,'count':len(cards)}

    def compact_evidence(self, bundle, max_chars=4200):
        parts=[]
        for i,c in enumerate(bundle.get('cards',[]),1):
            facts='\n'.join(f'- {s}' for s in c.get('sentences',[])[:4])
            part=(
                f"FONTE {i} | {c.get('source_type')} | autoridade {c.get('authority_score')}\n"
                f"Título: {c.get('title')}\nURL: {c.get('url')}\nData: {c.get('published') or 'não identificada'}\n{facts}"
            )
            parts.append(part)
        joined='\n\n'.join(parts)
        return joined[:int(max_chars)]

    def deterministic_summary(self, bundle):
        cards=bundle.get('cards',[])
        official=[c for c in cards if c.get('official')]
        bullets=[]; seen=set()
        for c in cards:
            for s in c.get('sentences',[])[:3]:
                key=re.sub(r'\W+',' ',s.lower())[:170]
                if key in seen: continue
                seen.add(key); bullets.append((c,s))
                if len(bullets)>=10: break
            if len(bullets)>=10: break
        lines=[
            f"Foram consultadas {len(cards)} fontes, com prioridade para fontes oficiais e de maior autoridade.",
            f"{len(official)} das fontes selecionadas foram classificadas como oficiais." if official else "Nenhuma das fontes coletadas foi classificada como oficial.",
            '', '### Pontos encontrados'
        ]
        for c,s in bullets:
            lines.append(f"- {s} _({c.get('domain')})_")
        return '\n'.join(lines)

    def compare_sources(self, cards):
        term_counter={}
        for c in cards:
            terms=set()
            for s in c.get('sentences',[]):
                terms.update(self._terms(s))
            for t in terms:
                term_counter[t]=term_counter.get(t,0)+1
        shared=[{'term':k,'sources':v} for k,v in sorted(term_counter.items(),key=lambda x:(-x[1],x[0])) if v>=2][:30]
        return {'ok':True,'shared_terms':shared,'sources':len(cards)}

    def markdown_report(self, query, bundle, synthesis=None, synthesis_error=None):
        cards=bundle.get('cards',[])
        lines=[f'# Pesquisa: {query}','',f'Data: {datetime.now().strftime("%d/%m/%Y %H:%M")}','']
        if synthesis:
            lines += ['## Síntese', '', synthesis.strip(), '']
        else:
            lines += ['## Síntese determinística', '', self.deterministic_summary(bundle), '']
            if synthesis_error:
                lines += ['> A síntese generativa local não concluiu dentro do orçamento. O relatório acima foi montado pelo Research Engine a partir das evidências coletadas.', '']
        lines += ['## Evidências por fonte','']
        for i,c in enumerate(cards,1):
            badge='OFICIAL' if c.get('official') else c.get('source_type','WEB').upper()
            lines += [
                f"### {i}. {c.get('title') or c.get('domain')}",
                f"**Tipo:** {badge}  ",
                f"**Autoridade:** {c.get('authority_score')}  ",
                f"**Domínio:** {c.get('domain')}  ",
                f"**URL final:** {c.get('url')}  ",
            ]
            if c.get('published'): lines.append(f"**Data identificada:** {c.get('published')}  ")
            lines.append('')
            for s in c.get('sentences',[])[:5]: lines.append(f'- {s}')
            if c.get('error'): lines.append(f"- _Falha ao coletar conteúdo completo: {c.get('error')}_")
            lines.append('')
        lines += ['## Fontes consultadas','']
        for c in cards:
            lines.append(f"- {c.get('title') or c.get('domain')} — {c.get('url')}")
        return '\n'.join(lines).strip()+'\n'

    def save_history(self, payload):
        if not self.history_path:
            return
        row={'time':datetime.now().isoformat(timespec='seconds'),**payload}
        try:
            with self.history_path.open('a',encoding='utf-8') as fh:
                fh.write(json.dumps(row,ensure_ascii=False,default=str)+'\n')
            self.last_path.write_text(json.dumps(row,indent=2,ensure_ascii=False,default=str),encoding='utf-8')
        except Exception:
            pass

    def recent(self, limit=15):
        if not self.history_path or not self.history_path.exists(): return []
        rows=[]
        for line in self.history_path.read_text(encoding='utf-8').splitlines()[-int(limit):]:
            try: rows.append(json.loads(line))
            except Exception: pass
        return rows

    def execute(self, operation, **params):
        q=params.get('query','')
        if operation=='normalize_url': return {'ok':True,'url':normalize_url(params.get('url',''))}
        if operation=='source_identity': return {'ok':True,**source_identity(params.get('url',''),query=q)}
        if operation=='authority_score':
            score,label=authority_score(params.get('url',''),query=q); return {'ok':True,'score':score,'source_type':label}
        if operation=='domain': return {'ok':True,'domain':domain_of(params.get('url',''))}
        if operation=='query_terms': return {'ok':True,'items':self._terms(q)}
        if operation=='query_variants': return {'ok':True,'items':self.query_variants(q)}
        if operation=='search': return self.search(q,params.get('limit',10),params.get('official_first',True))
        if operation=='search_official': return self.search(q,params.get('limit',10),True)
        if operation=='rank_results': return {'ok':True,'items':self.rank_results(params.get('items',[]),q)}
        if operation=='dedupe_results': return {'ok':True,'items':self.dedupe_results(params.get('items',[]))}
        if operation=='fetch_source': return self.fetch_source(params.get('url',''),query=q)
        if operation=='evidence_card': return {'ok':True,'card':self.evidence_card(params,q)}
        if operation=='evidence_pack': return self.evidence_pack(q,params.get('limit',5),params.get('official_first',True))
        if operation=='compact_evidence': return {'ok':True,'text':self.compact_evidence(params.get('bundle',{}),params.get('max_chars',4200))}
        if operation=='deterministic_summary': return {'ok':True,'text':self.deterministic_summary(params.get('bundle',{}))}
        if operation=='compare_sources': return self.compare_sources(params.get('cards',[]))
        if operation=='markdown_report': return {'ok':True,'text':self.markdown_report(q,params.get('bundle',{}),params.get('synthesis'),params.get('synthesis_error'))}
        if operation=='recent': return {'ok':True,'items':self.recent(params.get('limit',15))}
        if operation=='analyze_url':
            fetched=self.fetch_source(params.get('url',''),query=q)
            if fetched.get('ok'):
                fetched['relevant_sentences']=self.extractor.relevant_sentences(fetched.get('text',''),q,params.get('limit',7))
            return fetched
        return {'ok':False,'error':f'Operação de pesquisa desconhecida: {operation}'}
