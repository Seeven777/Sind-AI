"""Direct Windows benchmark for Computer Runtime V2.

This bypasses the Jarvis conversation router and exercises the physical runtime
itself. Default behavior opens/selects a WhatsApp conversation only. It never
sends a message. `--draft` may type and verify a draft, but still never sends.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

from runtime.phase4.controls import choose_text_field
from runtime.phase4.intent import identity
from runtime.phase4.whatsapp_uia import WhatsAppUIA


def wait(ui, contact, message, predicate, timeout=12.0):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        last = ui.observe(contact, message)
        if last.get("ok") and predicate(last):
            return last
        time.sleep(0.20)
    return last or {"ok": False, "error": "timeout"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--contact", default="Me (você)")
    parser.add_argument("--draft", default=None)
    args = parser.parse_args()

    contact = str(args.contact).strip()
    ui = WhatsAppUIA()
    report = {
        "ok": False,
        "contact": contact,
        "draft_requested": args.draft is not None,
        "sent": False,
        "steps": [],
    }

    try:
        ui.open()
        report["steps"].append("whatsapp_open")

        snap = wait(ui, contact, "__benchmark__", lambda s: bool(s.get("controls")))
        if not snap.get("ok"):
            raise RuntimeError(snap.get("error") or "WhatsApp não ficou observável")

        if identity(snap.get("conversation")) != identity(contact):
            search = choose_text_field(snap["controls"], purpose="search")
            ui.set_text(search["key"], contact)
            report["steps"].append("search_written")

            snap = wait(
                ui, contact, "__benchmark__",
                lambda s: s.get("search_value") == contact and bool(s.get("contacts")),
            )
            contacts = [x for x in snap.get("contacts", []) if identity(x.get("name")) == identity(contact)]
            if len(contacts) != 1:
                raise RuntimeError(f"Resultado exato/único não apareceu: {len(contacts)}")
            report["steps"].append("contact_unique")

            ui.open_contact(contacts[0]["key"])
            report["steps"].append("contact_activated")

        snap = wait(
            ui, contact, args.draft or "__benchmark__",
            lambda s: identity(s.get("conversation")) == identity(contact) and bool(s.get("composer")),
        )
        if identity(snap.get("conversation")) != identity(contact):
            raise RuntimeError("Cabeçalho da conversa não foi verificado no painel direito.")
        report["steps"].append("conversation_verified")
        report["composer"] = snap.get("composer")
        report["draft_before"] = snap.get("draft")

        if args.draft is not None:
            draft = str(args.draft)
            if snap.get("draft") not in ("", draft):
                raise RuntimeError("Existe outro rascunho; foi preservado.")
            composer = choose_text_field(snap["controls"], purpose="message")
            if snap.get("draft") != draft:
                ui.set_text(composer["key"], draft)
            snap = wait(
                ui, contact, draft,
                lambda s: identity(s.get("conversation")) == identity(contact) and s.get("draft") == draft,
            )
            if snap.get("draft") != draft:
                raise RuntimeError("Rascunho não foi relido exatamente.")
            report["steps"].append("draft_verified")
            report["draft_after"] = draft

        report["ok"] = True
    except Exception as exc:
        report["error"] = str(exc)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print("\nIMPORTANTE: nenhuma mensagem foi enviada.")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
