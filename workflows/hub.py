import json
from pathlib import Path
import re
import unicodedata

RISK_ORDER={"read":0,"act":1,"write":2,"high":3,"critical":4}


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


class WorkflowHub:
    def __init__(self,catalog_path,action_hub):
        self.catalog_path=Path(catalog_path);self.actions=action_hub;self.reload()

    def reload(self):
        data=json.loads(self.catalog_path.read_text(encoding='utf-8'))
        self.items=data.get('workflows',[]) if isinstance(data,dict) else data
        self.by_id={x['id']:x for x in self.items}

    def stats(self):
        groups={};risks={}
        for x in self.items:
            groups[x.get('group','other')]=groups.get(x.get('group','other'),0)+1
            risks[x.get('risk','read')]=risks.get(x.get('risk','read'),0)+1
        return {'ok':True,'workflows':len(self.items),'groups':groups,'risks':risks}

    def search(self,query,limit=15):
        q,terms=_search_terms(query);ranked=[]
        for item in self.items:
            hay=_norm_search(" ".join([
                item.get("id",""), item.get("name",""), item.get("group",""),
                item.get("description",""), " ".join(item.get("keywords",[]))
            ]))
            score=12 if q and q in hay else 0
            matched=0
            for term in terms:
                if term and term in hay:
                    score+=3
                    matched+=1
            score += matched * matched
            if score:ranked.append((score,item))
        ranked.sort(key=lambda x:(-x[0],x[1]["id"]))
        out=[]
        for _,item in ranked[:int(limit)]:
            out.append({
                "id":item["id"],"name":item.get("name"),"group":item.get("group"),
                "description":item.get("description"),"risk":item.get("risk","read"),
                "inputs":item.get("inputs",{}),"steps":len(item.get("steps",[]))
            })
        return {"ok":True,"items":out,"count":len(ranked)}

    def get(self,workflow_id):return self.by_id.get(str(workflow_id))

    def _render(self,value,params):
        if isinstance(value,str):
            stripped=value.strip()
            if stripped.startswith('{{') and stripped.endswith('}}') and stripped.count('{{')==1:
                key=stripped[2:-2].strip()
                if key in params:
                    return params[key]
            out=value
            for k,v in params.items():out=out.replace('{{'+str(k)+'}}',str(v))
            return out
        if isinstance(value,list):return [self._render(v,params) for v in value]
        if isinstance(value,dict):return {k:self._render(v,params) for k,v in value.items()}
        return value

    def _step_action(self,step):
        return step.get('action') or step.get('action_id')

    def validate(self):
        missing=[];bad=[]
        for wf in self.items:
            for idx,step in enumerate(wf.get('steps',[]),1):
                aid=self._step_action(step)
                if not aid:bad.append({'workflow':wf.get('id'),'step':idx,'error':'sem action/action_id'});continue
                if not self.actions.get(aid):missing.append({'workflow':wf.get('id'),'step':idx,'action':aid})
        return {'ok':not missing and not bad,'missing_actions':missing,'invalid_steps':bad,'workflows':len(self.items)}

    def execute(self,workflow_id,params=None,status=None):
        item=self.get(workflow_id)
        if not item:return {'ok':False,'error':f'Workflow não encontrado: {workflow_id}'}
        params=dict(params or {})
        missing=[k for k,spec in item.get('inputs',{}).items() if spec.get('required') and params.get(k) in (None,'')]
        if missing:return {'ok':False,'error':'Entradas obrigatórias ausentes: '+', '.join(missing)}
        results=[]
        for index,step in enumerate(item.get('steps',[]),1):
            aid=self._step_action(step);meta=self.actions.get(aid) if aid else None
            if not meta:return {'ok':False,'error':f'Ação ausente no catálogo: {aid}','results':results}
            # New catalog style: explicit params with {{variables}}.
            if 'params' in step:
                action_params=self._render(step.get('params') or {},params)
            else:
                # Legacy style: fixed values + matching workflow inputs + action defaults.
                action_params={}
                for key in meta.get('params',{}):
                    if key in (step.get('fixed') or {}):action_params[key]=self._render(step['fixed'][key],params)
                    elif key in params:action_params[key]=params[key]
                    else:
                        default=meta.get('params',{}).get(key,{}).get('default')
                        if default is not None:action_params[key]=default
            if status:status(f"Workflow {item.get('name')}: {index}/{len(item.get('steps',[]))}")
            result=self.actions.execute(aid,action_params)
            results.append({'action':aid,'params':action_params,'result':result})
            if not result.get('ok') and not step.get('continue_on_error',False):
                return {'ok':False,'workflow':workflow_id,'name':item.get('name'),'failed_action':aid,'error':result.get('error','Falha no workflow.'),'results':results}
        return {'ok':True,'workflow':workflow_id,'name':item.get('name'),'steps':len(results),'results':results}
