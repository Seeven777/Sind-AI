import asyncio
from pathlib import Path

from jarvis.app.product_runtime import start_product_runtime
from jarvis.models import MockModelProvider


def test_local_inbox_sync_persists_real_file(tmp_path:Path):
    async def scenario():
        data=tmp_path/'data'
        inbox=data/'connectors'/'inbox'
        inbox.mkdir(parents=True)
        (inbox/'URGENTE prazo.txt').write_text(
            'Precisamos revisar esta entrega hoje.',encoding='utf-8'
        )
        rt=await start_product_runtime(data,model_provider=MockModelProvider())
        try:
            items=rt.connector_repository.unread()
            assert len(items)==1
            assert items[0]['title']=='URGENTE prazo'
            assert items[0]['priority']==85
            assert 'revisar esta entrega' in items[0]['content']
            assert rt.connector_repository.counts()['unread']==1
        finally:
            await rt.close()
    asyncio.run(scenario())


def test_calendar_ics_is_parsed(tmp_path:Path):
    async def scenario():
        data=tmp_path/'data'
        cal=data/'connectors'/'calendar.ics'
        cal.parent.mkdir(parents=True)
        cal.write_text(
            'BEGIN:VCALENDAR\n'
            'BEGIN:VEVENT\n'
            'UID:test-1\n'
            'DTSTART:20991231T150000Z\n'
            'DTEND:20991231T160000Z\n'
            'SUMMARY:Reunião futura\n'
            'LOCATION:Sala 1\n'
            'DESCRIPTION:Revisão do projeto\n'
            'END:VEVENT\n'
            'END:VCALENDAR\n',
            encoding='utf-8'
        )
        rt=await start_product_runtime(data,model_provider=MockModelProvider())
        try:
            events=rt.connector_repository.upcoming_events('2099-01-01T00:00:00+00:00')
            assert len(events)==1
            assert events[0]['title']=='Reunião futura'
            assert events[0]['metadata']['location']=='Sala 1'
        finally:
            await rt.close()
    asyncio.run(scenario())
