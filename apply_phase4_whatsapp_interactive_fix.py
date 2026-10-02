"""Apply the Phase 4 multi-turn WhatsApp integration to core/agent.py.

This is intentionally a surgical patch because core/agent.py is a large file
that may already include local project changes. The script is idempotent and
backs up the file before writing.
"""
from __future__ import annotations

import py_compile
import shutil
import sys
from pathlib import Path


IMPORT_LINE = (
    "from runtime.phase4.whatsapp_interactive import "
    "WhatsAppInteractiveExecutor, parse_whatsapp_interactive\n"
)

METHOD_BLOCK = r'''
    def _run_whatsapp_interactive(self, command, status=None, confirm_callback=None):
        """Execute a verified partial WhatsApp command across conversation turns."""
        session = self._execution_session()
        state = getattr(self, "_phase4_whatsapp_state", None)
        if not isinstance(state, dict):
            state = {"contact": "", "draft": "", "uncertain": False}
            self._phase4_whatsapp_state = state

        task_id = self.tasks.start(session.text if session else "Interação WhatsApp Desktop")
        self._active_task_id = task_id
        executor = None
        try:
            if status:
                status("Executando interação verificada no WhatsApp Desktop")

            def event(item):
                if not self._active_task_id:
                    return
                try:
                    step = len(executor.events) if executor is not None else 0
                    self.tasks.event(
                        self._active_task_id,
                        step,
                        "whatsapp_interactive_" + str(item.get("phase", "event")),
                        {},
                        {"ok": item.get("ok", item.get("verified", True)), **item},
                    )
                except Exception:
                    pass

            executor = WhatsAppInteractiveExecutor(
                WhatsAppUIA(),
                timeout=self.config.get("phase4_timeout_seconds", 12),
                cancelled=self._check_cancelled,
                event=event,
            )

            result = None

            if command.select:
                result = executor.select_conversation(command.contact)
                if result.get("goal_verification", {}).get("verified"):
                    state["contact"] = command.contact
                    state["draft"] = result.get("draft") or ""
                    state["uncertain"] = False
                else:
                    state["contact"] = ""
                    state["draft"] = ""

            if result is None or result.get("goal_verification", {}).get("verified"):
                if command.type_text:
                    contact = command.contact or state.get("contact", "")
                    result = executor.type_draft(contact, command.message)
                    if result.get("goal_verification", {}).get("verified"):
                        state["contact"] = contact
                        state["draft"] = command.message
                        state["uncertain"] = False

            if result is None or result.get("goal_verification", {}).get("verified"):
                if command.send:
                    contact = command.contact or state.get("contact", "")
                    message = command.message if command.type_text else state.get("draft", "")
                    if not message and contact:
                        current = executor.read_current_draft(contact)
                        if current.get("ok"):
                            message = current.get("draft") or ""
                            state["draft"] = message
                        else:
                            result = {
                                "ok": False,
                                "status": "failed",
                                "error": current.get("error", "Não consegui ler o rascunho atual."),
                                "goal_verification": {
                                    "verified": False,
                                    "scope": "goal",
                                    "reason": current.get("error", "Não consegui ler o rascunho atual."),
                                },
                            }
                    if result is None or result.get("goal_verification", {}).get("verified"):
                        result = executor.send_current(
                            contact,
                            message,
                            confirm=confirm_callback,
                            require_confirmation=self.config.get("deep_access", {}).get(
                                "confirm_risky_controls", True
                            ),
                        )
                        if result.get("goal_verification", {}).get("verified"):
                            state["contact"] = contact
                            state["draft"] = ""
                            state["uncertain"] = False
                        elif result.get("tool_execution", {}).get("send_attempted"):
                            state["uncertain"] = True

            if result is None:
                result = {
                    "ok": False,
                    "status": "failed",
                    "error": "Nenhuma etapa executável foi reconhecida.",
                    "goal_verification": {
                        "verified": False,
                        "scope": "goal",
                        "reason": "Nenhuma etapa executável foi reconhecida.",
                    },
                }

            verified = bool(result.get("goal_verification", {}).get("verified"))
            if command.send:
                answer = summarize_whatsapp(result)
            elif command.type_text and verified:
                answer = (
                    f'Texto inserido e verificado no campo de mensagem da conversa '
                    f'"{state.get("contact", "")}". Nenhuma mensagem foi enviada.'
                )
            elif command.select and verified:
                answer = (
                    f'Conversa "{state.get("contact", command.contact)}" aberta e verificada '
                    'no WhatsApp. Nenhuma mensagem foi enviada.'
                )
            else:
                answer = "Não concluí a interação no WhatsApp: " + str(
                    result.get("error") or result.get("goal_verification", {}).get("reason") or
                    "não foi possível verificar o objetivo."
                )

            if session:
                session.result = result
                session.special_answer = answer

            self.tasks.finish(task_id, answer, status="completed" if verified else "failed")
            self._last_response_metadata.update({
                "real_execution": True,
                "whatsapp_interactive": True,
                "execution_status": result.get("status"),
                "goal_verification": result.get("goal_verification"),
            })
            return answer
        finally:
            self._active_task_id = None

'''

ROUTING_OLD = '''        execution_intent = classify_intent(user_text)\n        if execution_intent.whatsapp:\n            return self._run_whatsapp_goal(execution_intent, status=status, confirm_callback=confirm_callback)\n'''

ROUTING_NEW = '''        execution_intent = classify_intent(user_text)\n        if execution_intent.whatsapp:\n            return self._run_whatsapp_goal(execution_intent, status=status, confirm_callback=confirm_callback)\n\n        interactive_whatsapp = parse_whatsapp_interactive(\n            user_text, state=getattr(self, "_phase4_whatsapp_state", None)\n        )\n        if interactive_whatsapp and interactive_whatsapp.handled:\n            return self._run_whatsapp_interactive(\n                interactive_whatsapp, status=status, confirm_callback=confirm_callback\n            )\n'''


def patch_text(text: str) -> tuple[str, list[str]]:
    changes = []

    if IMPORT_LINE not in text:
        marker = "from runtime.phase4.whatsapp import WhatsAppExecutor, summarize_whatsapp\n"
        if marker not in text:
            raise RuntimeError("Import marker da Fase 4 não encontrado em core/agent.py.")
        text = text.replace(marker, marker + IMPORT_LINE, 1)
        changes.append("import")

    if "    def _run_whatsapp_interactive(" not in text:
        marker = "    def _run_whatsapp_goal(self, intent, status=None, confirm_callback=None):\n"
        if marker not in text:
            raise RuntimeError("Método _run_whatsapp_goal da Fase 4 não encontrado.")
        text = text.replace(marker, METHOD_BLOCK + marker, 1)
        changes.append("method")

    if "interactive_whatsapp = parse_whatsapp_interactive(" not in text:
        if ROUTING_OLD not in text:
            raise RuntimeError("Bloco de roteamento WhatsApp da Fase 4 não encontrado.")
        text = text.replace(ROUTING_OLD, ROUTING_NEW, 1)
        changes.append("routing")

    return text, changes


def main():
    root = Path(__file__).resolve().parent
    # When executed after extracting the overlay on top of the project, this
    # script sits at the repository root.
    agent = root / "core" / "agent.py"
    if not agent.exists():
        print("ERRO: core/agent.py não encontrado. Extraia o overlay na raiz do projeto.")
        return 2

    original = agent.read_text(encoding="utf-8")
    try:
        patched, changes = patch_text(original)
    except Exception as exc:
        print(f"ERRO: {exc}")
        return 3

    if not changes:
        print("OK: correção multi-turn do WhatsApp já está aplicada.")
        return 0

    backup = agent.with_suffix(".py.phase4-interactive.bak")
    if not backup.exists():
        shutil.copy2(agent, backup)

    agent.write_text(patched, encoding="utf-8")
    try:
        py_compile.compile(str(agent), doraise=True)
    except Exception as exc:
        shutil.copy2(backup, agent)
        print(f"ERRO de sintaxe; core/agent.py restaurado do backup: {exc}")
        return 4

    print("OK: core/agent.py atualizado: " + ", ".join(changes))
    print("Backup: " + str(backup))
    return 0


if __name__ == "__main__":
    sys.exit(main())
