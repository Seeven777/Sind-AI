import tempfile
from pathlib import Path
from cognitive.conversation_store import ConversationStore
from cognitive.learning import LearningJournal
from cognitive.semantic_memory import SemanticMemory
from public_data.engine import PublicDataEngine
BASE=Path(__file__).resolve().parent

def check(name,condition,detail=""):
    if not condition:raise AssertionError(f"{name}: {detail}")
    print(f"[OK] {name}")

def main():
    with tempfile.TemporaryDirectory() as raw:
        td=Path(raw)
        c=ConversationStore(td/'conversations.db');sid1=c.current_session_id
        c.append('user','Estamos preparando uma pesquisa sobre NR-1 e riscos psicossociais.')
        c.append('assistant','Vou priorizar fontes oficiais do trabalho.')
        c.new_session('Outro assunto');c.append('user','Hoje estamos falando sobre outra pauta.')
        check('Conversa persiste',c.stats()['messages']==3,c.stats())
        check('Recuperação entre conversas',c.search('NR-1 riscos psicossociais',all_sessions=True)['count']>=1)
        c.set_current(sid1);ctx=c.context_messages('NR-1',recent_limit=2,relevant_limit=3,max_chars=2000)
        check('Contexto recuperável',any('NR-1' in x['content'] for x in ctx),ctx)
        l=LearningJournal(td/'learning.db');learned=l.learn_from_user('Prefiro fontes oficiais antes de blogs')
        check('Aprendizado explícito',learned['learned'],learned)
        check('Lição recuperada',any('fontes oficiais' in x['lesson'].lower() for x in l.relevant('pesquisa fontes oficiais')))
        semantic=SemanticMemory(td/'semantic.db','http://127.0.0.1:11434/api/chat','nomic-embed-text-v2-moe',enabled=False)
        check('Semantic memory optional by default',semantic.stats()['enabled'] is False)
        check('Semantic Ollama base normalized',semantic.ollama_url=='http://127.0.0.1:11434',semantic.ollama_url)

        e=PublicDataEngine(BASE/'public_data'/'registry.json',td/'proposals.json');s=e.stats()
        check('Registro público >= 28',s['sources']>=28,s);check('Fontes oficiais >= 10',s['official']>=10,s)
        check('IBGE recomendado',any(x['id']=='ibge' for x in e.recommend('população municípios do Brasil',5)['items']))
        check('DataJud recomendado',any(x['id']=='datajud' for x in e.recommend('processos judiciais tribunais',5)['items']))
        check('MTE recomendado',any(x['id']=='mte_pdet' for x in e.recommend('emprego mercado de trabalho rais caged',5)['items']))
        check('BCB recomendado',any(x['id']=='bcb_dados_abertos' for x in e.recommend('selic juros câmbio',5)['items']))
        check('Dados Abertos SP recomendado',any(x['id']=='dados_abertos_sp' for x in e.recommend('dados estaduais trabalho comércio São Paulo',8)['items']))
        check('Operações documentadas','municipalities' in e.get_source('ibge')['data'].get('operations',[]))
        print('\nCognitive Foundation offline test concluído.')
if __name__=='__main__':main()
