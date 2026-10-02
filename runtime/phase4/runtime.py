"""Per-request execution ledger and model-independent completion barrier."""
import re
from .intent import classify_intent, fold

DESKTOP_TOOLS = (
    "whatsapp_send_message",
    "open_app",
    "list_windows",
    "select_window",
    "inspect_selected_window",
    "click_control",
    "type_text",
    "press_key",
    "take_screenshot",
)
DESKTOP_ACTIONS = {
    "open_app",
    "open_url",
    "open_folder",
    "select_window",
    "click_control",
    "type_text",
    "press_key",
    "set_clipboard",
}
MUTATING_TOOLS = DESKTOP_ACTIONS | {
    "create_file",
    "create_folder",
    "copy_item",
    "move_item",
    "rename_item",
    "delete_item",
    "execute_action",
    "execute_workflow",
    "execute_capability",
    "run_skill",
    "run_workplace_playbook",
    "create_long_job",
    "whatsapp_send_message",
}
READ_TOOLS = {
    "list_windows",
    "list_processes",
    "inspect_selected_window",
    "take_screenshot",
    "get_world_state",
    "get_clipboard",
    "read_file",
    "list_files",
    "search_actions",
    "search_capabilities",
    "set_task_plan",
    "resolve_capability",
    "search_web",
    "fetch_public_url",
}

WHATSAPP_SCHEMA = {
    "type": "function",
    "function": {
        "name": "whatsapp_send_message",
        "description": (
            "Envia uma única mensagem explícita pelo WhatsApp Desktop e verifica a "
            "interface. Não invente contato/texto; não repita envio incerto."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "contact": {"type": "string"},
                "message": {"type": "string"},
            },
            "required": ["contact", "message"],
            "additionalProperties": False,
        },
    },
}


def observe_desktop(controller):
    try:
        return {
            "window": controller.snapshot(),
            "ui": controller.inspect_selected(max_controls=300),
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


class ExecutionSession:
    def __init__(self, text):
        self.text = text
        self.intent = classify_intent(text)
        self.records = []
        self.result = None
        self.special_answer = None
        self.whatsapp_attempted = False

    def record(self, name, args, result, before=None, after=None):
        self.records.append(
            {
                "tool": name,
                "args": dict(args),
                "tool_execution": {"ok": bool(result.get("ok"))},
                "error": result.get("error"),
                "verification": result.get("verification", {}),
                "before": before,
                "after": after,
            }
        )

    def goal_verification(self):
        if self.result is not None:
            return self.result.get("goal_verification", {"verified": False})
        t = fold(self.text).strip().rstrip(".!?")
        t = re.sub(r"^(?:por favor,?\s*|jarvis,?\s*)", "", t)
        actions = [r for r in self.records if r["tool"] not in READ_TOOLS]
        if len(actions) == 1:
            row = actions[0]
            if row["tool"] == "open_app":
                target = fold(row["args"].get("app", ""))
                if t in (
                    "abra " + target,
                    "abra o " + target,
                    "abrir " + target,
                    "abre " + target,
                ):
                    if row["verification"].get("verified"):
                        return {
                            "verified": True,
                            "scope": "goal",
                            "reason": row["verification"].get("reason"),
                            "answer": "Aplicativo aberto; a janela foi observada no desktop.",
                        }
            if row["tool"] == "type_text":
                from access.commands import parse_access_command

                command = parse_access_command(self.text)
                if (
                    command
                    and command.get("action") == "type_text"
                    and command.get("text") == row["args"].get("text")
                    and row["verification"].get("verified")
                ):
                    return {
                        "verified": True,
                        "scope": "goal",
                        "reason": "Texto literal relido no campo de destino.",
                        "answer": (
                            "Texto inserido e verificado no campo de destino. "
                            "Nenhum envio foi confirmado."
                        ),
                    }
        return {
            "verified": False,
            "scope": "goal",
            "reason": "O objetivo completo não possui evidência verificável suficiente.",
        }

    def final_answer(self, answer):
        if not self.intent.executable:
            return answer
        if self.special_answer:
            return self.special_answer
        if self.result is not None:
            from .whatsapp import summarize_whatsapp

            return summarize_whatsapp(self.result)
        verification = self.goal_verification()
        if verification.get("verified"):
            return verification["answer"]
        count = sum(
            1
            for row in self.records
            if row["tool"] not in READ_TOOLS and row["tool_execution"]["ok"]
        )
        if count:
            return (
                f"Executei {count} etapa(s), mas não consegui verificar o objetivo completo. "
                "Não considero a tarefa concluída. Confira o estado atual antes de repetir a ação."
            )
        errors = [str(r["error"]) for r in self.records if r.get("error")]
        detail = (" Motivo: " + errors[-1]) if errors else ""
        return (
            "Não concluí a ação solicitada: não há execução física verificada para este pedido. "
            "Nenhum sucesso foi confirmado." + detail
        )


def verify_open_app(app):
    """Verify the actual native window, not merely a successful launcher call."""
    try:
        import os

        if os.name != "nt":
            return {"verified": False, "reason": "Desktop Windows indisponível."}

        if fold(app) in ("whatsapp", "whats app"):
            from .whatsapp_uia import discover_whatsapp_windows

            discovery = discover_whatsapp_windows()
            if discovery.get("chosen"):
                chosen = discovery["chosen"]
                return {
                    "verified": True,
                    "scope": "tool",
                    "reason": (
                        "Janela visível do pacote WhatsApp.Root/WebView2 observada "
                        f"(processo {chosen.get('exe')}, pid {chosen.get('pid')})."
                    ),
                }
            return {
                "verified": False,
                "reason": discovery.get("error")
                or "Não observei uma janela utilizável do WhatsApp.",
            }

        from pywinauto import Desktop
        from .whatsapp_uia import process_basename

        names = {
            "notepad": "notepad.exe",
            "bloco de notas": "notepad.exe",
            "calc": "calculatorapp.exe",
            "calculadora": "calculatorapp.exe",
            "paint": "mspaint.exe",
            "explorer": "explorer.exe",
            "explorador": "explorer.exe",
        }
        process = names.get(fold(app))
        if process:
            import time

            deadline = time.monotonic() + 5
            while True:
                for window in Desktop(backend="uia").windows():
                    if (
                        window.is_visible()
                        and process_basename(window.element_info.process_id) == process
                    ):
                        return {
                            "verified": True,
                            "scope": "tool",
                            "reason": (
                                "Janela visível do processo solicitado observada via UIA."
                            ),
                        }
                if time.monotonic() >= deadline:
                    break
                time.sleep(0.2)
        return {
            "verified": False,
            "reason": "Não observei uma janela nativa do aplicativo solicitado.",
        }
    except Exception as exc:
        return {"verified": False, "reason": str(exc)}
