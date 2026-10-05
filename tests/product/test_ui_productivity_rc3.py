from pathlib import Path


def test_rc3_ui_contract():
    root=Path(__file__).resolve().parents[2]
    companion=(root/'src/jarvis/ui/hq_web/companion.html').read_text(encoding='utf-8')
    js=(root/'src/jarvis/ui/hq_web/companion.js').read_text(encoding='utf-8')
    office=(root/'src/jarvis/ui/hq_web/index.html').read_text(encoding='utf-8')
    assert 'id="history"' in companion
    assert '/api/conversations' in js
    assert 'action:\'regenerate\'' in js
    assert 'importmap' in office
    assert 'three@0.186.1' in office
    migration=(root/'migrations/0006_conversation_ui.sql').read_text(encoding='utf-8')
    assert 'archived' in migration and 'pinned' in migration
