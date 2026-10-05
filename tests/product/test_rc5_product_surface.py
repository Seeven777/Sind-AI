from pathlib import Path

import asyncio

from jarvis.app.bootstrap import start_runtime
from jarvis.storage.repositories.product import MemoryRepository
from jarvis.tools.builtin import WriteWorkspacePdfTool


def test_workspace_pdf_is_created_and_verifiable(tmp_path):
    tool = WriteWorkspacePdfTool(tmp_path)
    result = tool.execute({
        'relative_path': 'reports/teste.pdf',
        'title': 'Relatório Jarvis',
        'content': '# Teste\n\nConteúdo com acentuação: ação, análise, memória.\n\n- item 1\n- item 2',
    })
    assert result.success is True
    verified = tool.verify({}, result)
    assert verified.success is True
    path = Path(result.output['path'])
    assert path.is_file()
    assert verified.evidence['pages'] == 1


def test_memory_repository_supports_forget(tmp_path):
    async def scenario():
        rt=await start_runtime(tmp_path)
        try:
            repo=MemoryRepository(rt.database.conn())
            mid=repo.add('Guardar isto',importance=.8)
            assert any(x['memory_id']==mid for x in repo.recent(10))
            assert repo.delete(mid) is True
            assert not any(x['memory_id']==mid for x in repo.recent(10))
        finally:
            await rt.close()
    asyncio.run(scenario())


def test_core_packaging_declares_pdf_runtime_dependencies():
    text = Path("pyproject.toml").read_text(encoding="utf-8")
    assert '"reportlab>=4.0"' in text
    assert '"pypdf>=6.0"' in text


def test_launcher_has_startup_capture_and_extended_grace_period():
    text = Path("Start-Jarvis-UI.ps1").read_text(encoding="utf-8-sig")
    assert "-RedirectStandardError $StderrLog" in text
    assert "$i -lt 240" in text
