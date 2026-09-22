from pathlib import Path
from cognitive.self_awareness import SelfAwareness
from institutional.services import InstitutionalServices
from institutional.service_runtime import InstitutionalServiceRuntime

BASE=Path(__file__).resolve().parent

class Stub:
    def stats(self): return {'actions':611,'workflows':474,'capabilities':237,'documents':0}
class Models:
    def status(self): return {'fast_model':'qwen3:1.7b','reasoning_model':'qwen3:4b'}
    def chat(self,*a,**k): return {'message':{'content':'Dashboard analisado sem inventar valores.'},'_jarvis_model':'qwen3:1.7b'}
class Hardware:
    def profile(self): return {'tier':'standard'}
class Browser:
    def inspect_page(self,url,wait_ms=0,max_chars=0):
        return {'ok':True,'url':url,'title':'Insights','text':'Visão geral do período. Alcance 1000. Interações 120. Seguidores 50. Compartilhamentos 20. Salvamentos 15. Reels 800 visualizações. Carrossel 620 visualizações.','headings':[{'text':'Visão geral'}],'tables':[]}

def check(name,cond,detail=''):
    if not cond: raise AssertionError(f'{name}: {detail}')
    print('[OK]',name)

services=InstitutionalServices(BASE/'data'/'institutional_services.json')
sa=SelfAwareness(services,Stub(),Stub(),Stub(),Models(),Hardware(),Stub(),connectors=Stub())
q='Quais ferramentas do SindPetshop-SP você conhece e quando usaria cada uma?'
check('Self awareness matches tools question',sa.matches(q))
ans=sa.answer(q)
check('Tools answer lists dashboard','Insights SindPetshop-SP' in ans,ans)
check('Tools answer lists Slack','Slack SindPetshop-SP' in ans,ans)
check('No generic dictionary source','Dicio' not in ans,ans)
q2='Você consegue acessar o Instagram?'
ans2=sa.answer(q2)
check('Specific Instagram grounding','Instagram SindPetshop-SP' in ans2,ans2)
rt=InstitutionalServiceRuntime(services,Browser(),Models())
q3='Veja nosso dashboard e me diga o que seria útil analisar antes da próxima publicação.'
check('Dashboard route matches',rt.matches(q3))
r=rt.run(q3)
check('Dashboard uses fast grounded route',r.get('ok') and r.get('grounded') and r.get('model')=='qwen3:1.7b',r)
print('\nSelf-awareness/service runtime test concluído.')
