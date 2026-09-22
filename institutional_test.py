import json
import tempfile
from pathlib import Path

from actions.hub import ActionHub
from content_ops.engine import ContentOps
from document_intelligence.engine import DocumentIntelligence
from governance.engine import GovernanceEngine
from institutional.store import InstitutionalStore
from institutional_knowledge.engine import InstitutionalKnowledge
from knowledge.base import KnowledgeBase
from training.engine import TrainingEngine

BASE=Path(__file__).resolve().parent

def ok(name,cond,detail=None):
    if not cond: raise AssertionError(f"{name}: {detail}")
    print(f"[OK] {name}")


def main():
    action_catalog=json.loads((BASE/'actions'/'catalog.json').read_text(encoding='utf-8'))['actions']
    workflow_catalog=json.loads((BASE/'workflows'/'catalog.json').read_text(encoding='utf-8'))['workflows']
    ok('Action Hub >= 480',len(action_catalog)>=480,len(action_catalog))
    ok('Workflow Hub >= 409',len(workflow_catalog)>=409,len(workflow_catalog))
    action_ids={x['id'] for x in action_catalog}
    missing=[]
    for wf in workflow_catalog:
        for step in wf.get('steps',[]):
            aid=step.get('action') or step.get('action_id')
            if aid not in action_ids:missing.append((wf['id'],aid))
    ok('Todos workflows apontam para ações existentes',not missing,missing[:10])

    with tempfile.TemporaryDirectory() as td_raw:
        td=Path(td_raw)
        kb=KnowledgeBase(td/'knowledge.db',td/'storage')
        docs=DocumentIntelligence(allowed_root=td)
        inst=InstitutionalStore(td/'institutional.db')
        ik=InstitutionalKnowledge(td/'institutional_knowledge.db',kb,docs,td/'workspace')
        training=TrainingEngine(td/'training.db',knowledge_engine=ik)
        content=ContentOps(td/'content.db',td/'workspace',institutional_store=inst)
        governance=GovernanceEngine(td/'governance.db')

        r=inst.execute('profile_set',key='organization_name',value='SindPetshop-SP')
        ok('Perfil institucional grava',r['ok'])
        r=inst.execute('glossary_create',term='CCT',definition='Convenção Coletiva de Trabalho')
        ok('Glossário grava',r['ok'])
        r=inst.execute('policy_create',title='Publicação externa',body='Publicar somente após aprovação.',category='content')
        ok('Política institucional grava',r['ok'])
        ctx=inst.execute('context_bundle')
        ok('Context bundle',ctx['ok'] and ctx['profile'].get('organization_name')=='SindPetshop-SP',ctx)

        cct=td/'cct_teste.txt'
        cct.write_text('''CONVENÇÃO COLETIVA DE TRABALHO\n\nCLÁUSULA 1 - PISO SALARIAL\nFica estabelecido piso salarial de teste.\n\nCLÁUSULA 2 - AUXÍLIO-CRECHE\nSerá concedido auxílio-creche conforme regras da categoria.\n\nCLÁUSULA 3 - SEGURO DE VIDA\nA empresa manterá seguro de vida conforme condições coletivas.''',encoding='utf-8')
        r=ik.execute('import_file',path=str(cct),title='CCT Teste',collection='cct')
        ok('CCT importada',r['ok'] and r['clauses']>=3,r)
        s=ik.execute('clause_search',query='auxílio-creche')
        ok('Pesquisa por cláusula',s['ok'] and s['count']>=1,s)
        e=ik.execute('evidence_pack',query='seguro de vida',collections=['cct'])
        ok('Evidence pack citável',e['ok'] and e['count']>=1 and e['items'][0].get('citation'),e)

        t=training.execute('track_create',name='Onboarding Comunicação',role='comunicação')
        ok('Trilha criada',t['ok'])
        m=training.execute('module_add',track_id=t['id'],title='Conhecer a CCT',collection='cct',query='benefícios')
        ok('Módulo criado',m['ok'])
        mat=training.execute('module_material',id=m['id'])
        ok('Módulo busca material institucional',mat['ok'],mat)
        q=training.execute('quiz_create',name='Quiz CCT',role='comunicação',module_id=m['id'])
        training.execute('question_add',quiz_id=q['id'],question='O que significa CCT?',answer='Convenção Coletiva de Trabalho',source='[KB:cct]')
        qg=training.execute('quiz_get',id=q['id'])
        ok('Quiz com pergunta',qg['ok'] and len(qg['data']['questions'])==1,qg)

        br=content.execute('brief_create',title='Post CCT',topic='Auxílio-creche',content_type='carousel',channel='instagram',sources=[{'url':'https://example.org','official':True}])
        ok('Briefing editorial criado',br['ok'])
        dr=content.execute('draft_create',brief_id=br['id'],title='Auxílio-creche',body='## Direito coletivo\n\nConfira sua CCT. Entre em contato.',content_type='carousel')
        ok('Rascunho versionado',dr['ok'])
        chk=content.execute('draft_check',id=dr['id'])
        ok('Validação editorial',chk['ok'] and chk['metrics']['has_cta'],chk)
        pkg=content.execute('package_create',name='auxilio_creche',brief_id=br['id'],draft_id=dr['id'])
        ok('Pacote editorial criado',pkg['ok'] and Path(pkg['path']).exists(),pkg)

        con=governance.execute('connector_create',name='WordPress Site',connector_type='wordpress',endpoint='https://example.org',status='enabled')
        governance.execute('permission_set',connector_id=con['id'],scope='posts',level='draft',requires_confirmation=True)
        pc=governance.execute('permission_check',connector_id=con['id'],scope='posts',requested_level='draft')
        ok('Governança permite draft',pc['ok'] and pc['allowed'],pc)
        pc2=governance.execute('permission_check',connector_id=con['id'],scope='posts',requested_level='publish')
        ok('Governança bloqueia publish sem escopo',pc2['ok'] and not pc2['allowed'],pc2)

        hub=ActionHub(BASE/'actions'/'catalog.json',{
            'institutional':inst,'institutional_knowledge':ik,'training':training,
            'content_ops':content,'governance':governance
        })
        sr=hub.search('CCT treinamento onboarding',limit=20)
        ok('Broker encontra ações institucionais',sr['ok'] and sr['count']>0,sr)
        ex=hub.execute('institutional.stats',{})
        ok('Action Hub executa engine institucional',ex['ok'],ex)

    print('\nInstitutional Intelligence 0.8: testes offline aprovados.')

if __name__=='__main__':main()
