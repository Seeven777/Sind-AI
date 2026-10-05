from __future__ import annotations

import asyncio
from pathlib import Path

from jarvis.app.product_runtime import start_product_runtime
from jarvis.models import MockModelProvider


def test_preferences_persist_in_system_kv(tmp_path: Path):
    async def run():
        rt = await start_product_runtime(tmp_path, model_provider=MockModelProvider("resposta longa o suficiente"))
        try:
            rt.preferences.set("default_mode", "deep")
            rt.preferences.set("compact", True)
            assert rt.preferences.all()["default_mode"] == "deep"
            assert rt.preferences.all()["compact"] is True
        finally:
            await rt.close()
    asyncio.run(run())


def test_conversation_export_markdown_and_json(tmp_path: Path):
    async def run():
        rt = await start_product_runtime(tmp_path, model_provider=MockModelProvider("resposta válida"))
        try:
            cid = rt.chat.new_conversation()
            await rt.chat.send(cid, "Olá")
            md = rt.chat.export_conversation(cid, "md")
            data = rt.chat.export_conversation(cid, "json")
            assert md.startswith("# ")
            assert "## Você" in md and "## Jarvis" in md
            assert len(data["messages"]) == 2
        finally:
            await rt.close()
    asyncio.run(run())


def test_chat_attachments_are_context_and_metadata(tmp_path: Path):
    async def run():
        provider = MockModelProvider("resposta válida")
        rt = await start_product_runtime(tmp_path, model_provider=provider)
        try:
            cid = rt.chat.new_conversation()
            await rt.chat.send(cid, "Analise o arquivo", attachments=[{"name": "notas.txt", "content": "conteúdo secreto de teste"}])
            convo = rt.chat.get_conversation(cid)
            assert "conteúdo secreto de teste" in convo["messages"][0]["content"]
            assert convo["messages"][0]["metadata"]["attachments"][0]["name"] == "notas.txt"
        finally:
            await rt.close()
    asyncio.run(run())


def test_fast_and_deep_modes_are_exposed(tmp_path: Path):
    async def run():
        rt = await start_product_runtime(tmp_path, model_provider=MockModelProvider("resposta suficientemente longa"))
        try:
            cid = rt.chat.new_conversation()
            fast = await rt.chat.send(cid, "responda", mode="fast")
            assert fast["kind"] == "chat"
            deep = await rt.chat.send(cid, "responda", mode="deep")
            assert deep["kind"] == "deep"
        finally:
            await rt.close()
    asyncio.run(run())


def test_rc4_ui_contains_productivity_surfaces():
    root = Path(__file__).resolve().parents[2] / "src/jarvis/ui/hq_web"
    companion = (root / "companion.html").read_text(encoding="utf-8")
    companion_js = (root / "companion.js").read_text(encoding="utf-8")
    office = (root / "index.html").read_text(encoding="utf-8")
    mission = (root / "mission-control.html").read_text(encoding="utf-8")
    assert "id=\"file-input\"" in companion
    assert "id=\"settings-modal\"" in companion
    assert "id=\"palette\"" in companion
    assert "/api/preferences" in companion_js
    assert "data-mode=\"hermes\"" in companion
    assert "Operational Office" in office
    assert "Mission cockpit" in office
    assert "NEW MISSION" in mission


def test_desktop_launcher_exists():
    root = Path(__file__).resolve().parents[2]
    assert (root / "Start-Jarvis-Desktop.cmd").is_file()
    assert (root / "Start-Jarvis-Desktop.ps1").is_file()
