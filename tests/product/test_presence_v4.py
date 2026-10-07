from pathlib import Path
import asyncio

from jarvis.app.product_runtime import start_product_runtime
from jarvis.models import MockModelProvider
from jarvis.voice import VoiceService


def test_combined_email_calendar_request_uses_live_briefing(tmp_path: Path):
    async def scenario():
        data = tmp_path / 'data'
        inbox = data / 'connectors' / 'inbox'
        inbox.mkdir(parents=True)
        (inbox / 'Mensagem.txt').write_text('Assunto real da caixa local', encoding='utf-8')
        rt = await start_product_runtime(data, model_provider=MockModelProvider())
        try:
            result = await rt.orchestrator.handle(
                'Jarvis, verifique meus compromissos e e-mails recentes e me diga o que merece minha atenção hoje.'
            )
            assert result['kind'] == 'briefing'
            assert 'E-mails / caixa de entrada recentes:' in result['content']
            assert 'Mensagem' in result['content']
            assert 'Acesso restrito' not in result['content']
        finally:
            await rt.close()
    asyncio.run(scenario())


def test_voice_service_exposes_zero_config_windows_fallback():
    health = VoiceService().health()
    assert 'windows_sapi' in health['tts_backends']
    assert health['tts_backends']['windows_sapi']['backend'] == 'windows-sapi'


def test_office_agents_are_bound_to_real_workstation_seats():
    root = Path(__file__).resolve().parents[2]
    js = (root / 'src/jarvis/ui/hq_web/office3d.js').read_text(encoding='utf-8')
    assert 'userData={type:\'room\',room:name,seats:[]}' in js
    assert 'roomObj?.userData?.seats?.[i]' in js
    assert 'CapsuleGeometry' in js
    assert 'target.add(towardCore.multiplyScalar(.06))' in js


def test_companion_core_has_visible_nucleus_and_pointer_response():
    root = Path(__file__).resolve().parents[2]
    js = (root / 'src/jarvis/ui/hq_web/jarvis-core.js').read_text(encoding='utf-8')
    assert 'float nucleus=' in js
    assert 'local=exp(-3.4*length' in js
    assert 'sphereCloud(shellCount=3600,innerCount=980)' in js
