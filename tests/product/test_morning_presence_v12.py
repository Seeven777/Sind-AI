import asyncio
from pathlib import Path

from jarvis.app.product_runtime import start_product_runtime
from jarvis.connectors.base import ConnectorItem
from jarvis.connectors.marketing_tasks import MarketingTasksConnector
from jarvis.models.mock import MockModelProvider


def test_marketing_task_record_normalization(tmp_path:Path):
    class Secrets:
        def get(self,*a,**k): return None
        def set(self,*a,**k): pass
        def delete(self,*a,**k): pass
    c=MarketingTasksConnector(app_url='https://example.invalid',state_path=tmp_path/'state.json',secret_store=Secrets())
    item=c._to_item({'id':'42','title':'Publicar carrossel','status':'Pendente','priority':'alta','due_date':'08/10/2026'},0,'https://example.invalid')
    assert item is not None
    assert item.item_type=='work_task'
    assert item.title=='Publicar carrossel'
    assert item.priority>=85
    assert item.occurred_at
    assert c._to_item({'id':'43','title':'Feito','status':'Concluído'},1,'x') is None


def test_morning_sequence_contains_structured_weather_news_and_tasks(tmp_path:Path):
    async def scenario():
        rt=await start_product_runtime(tmp_path,model_provider=MockModelProvider('ok'))
        try:
            rt.autonomy_repository.set_state('daily_briefing',{
                'date':'2026-10-08','location':'São Paulo, SP',
                'weather':{
                    'summary':'Agora 24 graus, parcialmente nublado.',
                    'structured':{
                        'location':'São Paulo, SP, Brasil',
                        'current':{'temperature':24,'condition':'parcialmente nublado','weather_code':2,'humidity':55,'wind_speed':8},
                        'today':{'temperature_max':28,'temperature_min':18,'precipitation_probability_max':20},
                        'units':{'temperature':'°C','humidity':'%','wind_speed':'km/h','probability':'%'},
                        'hourly':[{'time':'2026-10-08T10:00','temperature':25,'weather_code':2}],
                    },
                    'sources':[{'title':'Open-Meteo','url':'https://open-meteo.com/'}],
                },
                'news':[{'title':'Notícia teste','summary':'Resumo','url':'https://example.com/n','source':'Example'}],
            })
            connector=rt.connector_registry.get('marketing.tasks')
            rt.connector_repository.upsert_item('marketing.tasks',ConnectorItem(
                external_id='t1',item_type='work_task',title='Tarefa pendente',content='Detalhes',priority=88,
                metadata={'status':'Pendente','app_url':connector.app_url}
            ))
            seq=rt.briefing.morning_sequence()
            assert seq['schema']=='jarvis.morning.v1'
            assert seq['weather']['current']['temperature']==24
            assert seq['news'][0]['url']=='https://example.com/n'
            assert seq['tasks'][0]['title']=='Tarefa pendente'
            assert seq['closing']=='O que faremos hoje?'
        finally:
            await rt.close()
    asyncio.run(scenario())


def test_morning_assets_are_wired():
    root=Path(__file__).resolve().parents[2]/'src/jarvis/ui/hq_web'
    companion=(root/'companion.html').read_text(encoding='utf-8')
    mobile=(root/'mobile.html').read_text(encoding='utf-8')
    js=(root/'morning-sequence.js').read_text(encoding='utf-8')
    css=(root/'morning-sequence.css').read_text(encoding='utf-8')
    assert '/morning-sequence.js' in companion and '/morning-sequence.css' in companion
    assert '/morning-sequence.js' in mobile and '/morning-sequence.css' in mobile
    assert 'weather-gadget' in js and 'news-constellation' in js and 'tasks-gadget' in js
    assert '.boot-sequence' in css and '.weather-gadget' in css


def test_manual_full_briefing_routes_to_interactive_sequence():
    from jarvis.brain.intent import IntentRouter
    router=IntentRouter()
    samples=[
        'Jarvis, faça meu briefing completo do dia.',
        'Refaça meu briefing de hoje',
        'Abra o briefing completo',
    ]
    for sample in samples:
        assert router.classify(sample).name=='morning_sequence'


def test_manual_briefing_frontends_refresh_live_data():
    root=Path(__file__).resolve().parents[2]/'src/jarvis/ui/hq_web'
    companion=(root/'companion.js').read_text(encoding='utf-8')
    mobile=(root/'mobile.js').read_text(encoding='utf-8')
    for js in (companion,mobile):
        assert "morningController.prepare(force)" in js
        assert "x.kind==='morning_sequence'" in js
    assert "force?await api('/api/morning')" not in companion
    assert "force?await api('/api/morning')" not in mobile


def test_v12_2_shell_busts_stale_service_worker_cache():
    root=Path(__file__).resolve().parents[2]/'src/jarvis/ui/hq_web'
    companion=(root/'companion.html').read_text(encoding='utf-8')
    mobile=(root/'mobile.html').read_text(encoding='utf-8')
    sw=(root/'sw.js').read_text(encoding='utf-8')
    assert 'companion.js?v=12.2' in companion
    assert 'morning-sequence.js?v=12.2' in companion
    assert 'mobile.js?v=12.2' in mobile
    assert "jarvis-shell-v12.2" in sw
    assert "fetch(req,{cache:'no-cache'})" in sw


def test_interactive_morning_action_does_not_persist_placeholder_reply(tmp_path:Path):
    async def scenario():
        rt=await start_product_runtime(tmp_path,model_provider=MockModelProvider('ok'))
        try:
            cid=rt.chat.new_conversation('Teste briefing')
            result=await rt.chat.send(cid,'Jarvis, faça meu briefing completo do dia.')
            assert result['ui_action']=='morning_sequence'
            convo=rt.chat.get_conversation(cid)
            assistant=[m for m in convo['messages'] if m['role']=='assistant']
            assert assistant==[]
        finally:
            await rt.close()
    asyncio.run(scenario())


def test_frontends_hide_legacy_morning_placeholder_messages():
    root=Path(__file__).resolve().parents[2]/'src/jarvis/ui/hq_web'
    companion=(root/'companion.js').read_text(encoding='utf-8')
    mobile=(root/'mobile.js').read_text(encoding='utf-8')
    for js in (companion,mobile):
        assert "m.metadata?.kind==='morning_sequence'" in js
        assert 'beginPreparing?.()' in js
