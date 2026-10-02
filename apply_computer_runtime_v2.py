"""Idempotent installer for Computer Runtime V2.

Run from the JARVIS project root after extracting this overlay.
It only patches core/agent.py; the remaining V2 files are installed by extraction.
"""
from __future__ import annotations

import re
import shutil
import sys
import time
from pathlib import Path

MARKER = "# COMPUTER_RUNTIME_V2_EARLY_WHATSAPP"


def fail(msg):
    print("ERRO:", msg)
    raise SystemExit(2)


def main():
    root = Path(__file__).resolve().parent
    agent_path = root / "core" / "agent.py"
    if not agent_path.exists():
        fail(f"core/agent.py não encontrado em {root}")

    text = agent_path.read_text(encoding="utf-8")
    original = text

    # Ensure imports required by the early deterministic route.
    if "from runtime.phase4.whatsapp_interactive import WhatsAppInteractiveExecutor, parse_whatsapp_interactive" not in text:
        anchor = "from runtime.phase4.whatsapp import WhatsAppExecutor, summarize_whatsapp\n"
        if anchor not in text:
            fail("Import de runtime.phase4.whatsapp não encontrado; base incompatível.")
        text = text.replace(
            anchor,
            anchor + "from runtime.phase4.whatsapp_interactive import WhatsAppInteractiveExecutor, parse_whatsapp_interactive\n",
            1,
        )

    if "from runtime.phase4.whatsapp_uia import WhatsAppUIA" not in text:
        anchor = "from runtime.phase4.whatsapp_interactive import WhatsAppInteractiveExecutor, parse_whatsapp_interactive\n"
        text = text.replace(anchor, anchor + "from runtime.phase4.whatsapp_uia import WhatsAppUIA\n", 1)

    if "def _run_whatsapp_interactive(" not in text:
        fail(
            "O método _run_whatsapp_interactive não existe em core/agent.py. "
            "Aplique primeiro a base Phase 4/Interactive WhatsApp ou use a branch feature/phase4-real-execution-runtime."
        )

    # Absolute precedence guard. This fixes the observed real-world symptom where
    # a compound `abra WhatsApp + selecione conversa` was being reduced to open_app.
    if MARKER not in text:
        pattern = re.compile(r"^(    def _run_internal\([^\n]*\):\n)", re.M)
        match = pattern.search(text)
        if not match:
            fail("Não encontrei def _run_internal(...) em core/agent.py.")
        block = (
            match.group(1)
            + f"        {MARKER}\n"
            + "        # Compound WhatsApp execution must be handled before any generic/fast path.\n"
            + "        try:\n"
            + "            _computer_v2_wa = parse_whatsapp_interactive(\n"
            + "                user_text, state=getattr(self, \"_phase4_whatsapp_state\", None)\n"
            + "            )\n"
            + "        except Exception:\n"
            + "            _computer_v2_wa = None\n"
            + "        _computer_v2_state = getattr(self, \"_phase4_whatsapp_state\", None) or {}\n"
            + "        _computer_v2_partial = bool(\n"
            + "            _computer_v2_wa and (\n"
            + "                _computer_v2_wa.select or _computer_v2_wa.type_text or\n"
            + "                (_computer_v2_wa.send and _computer_v2_state.get(\"contact\"))\n"
            + "            )\n"
            + "        )\n"
            + "        if _computer_v2_partial:\n"
            + "            return self._run_whatsapp_interactive(\n"
            + "                _computer_v2_wa, status=status, confirm_callback=confirm_callback\n"
            + "            )\n\n"
        )
        text = text[: match.start()] + block + text[match.end() :]

    # Tell the local model that press_key also accepts common shortcuts. No new
    # tool name is introduced, so the existing tool budget/routing stays intact.
    text = text.replace(
        '"description":"Pressiona uma tecla segura na janela selecionada."',
        '"description":"Pressiona uma tecla ou atalho comum na janela selecionada (ex.: enter, tab, ctrl+f, ctrl+a, alt+f4, pagedown)."',
    )

    # `desktop` tool relevance can now be triggered by shortcut/mouse vocabulary too.
    old = '["janela","clique","botão","botao","digite","pressione","menu","interface","desktop"]'
    new = '["janela","clique","botão","botao","digite","pressione","atalho","tecla","menu","interface","desktop","mouse","rolar"]'
    text = text.replace(old, new)

    backup_dir = root / "backups" / ("computer_runtime_v2_" + time.strftime("%Y%m%d_%H%M%S"))
    backup_dir.mkdir(parents=True, exist_ok=True)

    if text != original:
        shutil.copy2(agent_path, backup_dir / "agent.py")
        agent_path.write_text(text, encoding="utf-8")
        print("core/agent.py atualizado. Backup:", backup_dir / "agent.py")
    else:
        print("core/agent.py já estava compatível com Computer Runtime V2.")

    # Archive obsolete micro-patch tests. They asserted superseded activation
    # strategies (unconditional Enter / old retry order) and can make the main
    # suite fail even when the rebuilt runtime is correct.
    obsolete_tests = (
        "test_phase4_conversation_activation.py",
        "test_phase4_verified_conversation_activation.py",
        "test_phase4_physical_activation_geometry.py",
    )
    legacy_dir = backup_dir / "legacy_tests"
    for name in obsolete_tests:
        src = root / "tests" / name
        if src.exists():
            legacy_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(legacy_dir / name))
            print("Teste legado arquivado:", name)

    # Static sanity checks that catch extraction into the wrong directory.
    required = [
        root / "runtime" / "computer_v2.py",
        root / "runtime" / "phase4" / "whatsapp_uia.py",
        root / "access" / "controller.py",
        root / "core" / "router.py",
    ]
    missing = [str(p.relative_to(root)) for p in required if not p.exists()]
    if missing:
        fail("Arquivos do overlay ausentes: " + ", ".join(missing))

    print("Computer Runtime V2 instalado.")
    print("Próximo passo: .\\.venv\\Scripts\\python.exe .\\run_computer_v2_tests.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
