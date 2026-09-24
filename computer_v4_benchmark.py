"""Direct physical benchmark for Computer Runtime V3 Raw Bridge.

No message is ever sent. With --draft, the script writes and verifies a draft
but deliberately stops before any send action.
"""
from __future__ import annotations

import argparse
import json
import sys
import time

from runtime.phase4.controls import choose_text_field
from runtime.phase4.intent import identity
from runtime.phase4.whatsapp_uia import WhatsAppUIA


def ensure_utf8():
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def wait(ui, contact, message, predicate, timeout=15.0):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        last = ui.observe(contact, message)
        if last.get("ok") and predicate(last):
            return last
        time.sleep(0.18)
    return last or {"ok": False, "error": "timeout"}


def main():
    ensure_utf8()
    parser = argparse.ArgumentParser()
    parser.add_argument("--contact", default="Me (você)")
    parser.add_argument("--draft", default=None)
    args = parser.parse_args()

    contact = str(args.contact).strip()
    ui = WhatsAppUIA()
    report = {
        "runtime": "computer-v4-hit-test",
        "ok": False,
        "contact": contact,
        "draft_requested": args.draft is not None,
        "sent": False,
        "steps": [],
        "diagnostics": {},
    }

    try:
        ui.open()
        report["steps"].append("whatsapp_open")

        snap = wait(
            ui, contact, "__benchmark__",
            lambda s: bool(s.get("controls")),
        )
        if not snap.get("ok"):
            raise RuntimeError(snap.get("error") or "WhatsApp não ficou observável")

        report["diagnostics"]["raw_bridge"] = bool(snap.get("raw_bridge"))
        report["diagnostics"]["search_value_initial"] = snap.get("search_value")
        report["diagnostics"]["conversation_initial"] = snap.get("conversation")

        if identity(snap.get("conversation")) != identity(contact):
            search = choose_text_field(snap["controls"], purpose="search")
            report["diagnostics"]["search_descriptor"] = {
                k: search.get(k)
                for k in (
                    "name", "automation_id", "control_type",
                    "bounds", "raw_search",
                )
            }

            ui.set_text(search["key"], contact)
            report["steps"].append("search_written")

            snap = wait(
                ui, contact, "__benchmark__",
                lambda s: s.get("search_value") == contact
                and len(s.get("contacts", [])) == 1,
            )
            report["diagnostics"]["search_value_after"] = snap.get("search_value")
            report["diagnostics"]["contacts_after_search"] = snap.get("contacts", [])

            contacts = [
                x for x in snap.get("contacts", [])
                if identity(x.get("name")) == identity(contact)
            ]
            if len(contacts) != 1:
                raise RuntimeError(
                    f"Resultado raw exato/único não apareceu: {len(contacts)}"
                )
            report["steps"].append("contact_unique")

            try:
                ui.open_contact(contacts[0]["key"])
                report["steps"].append("contact_activated")
            finally:
                report["diagnostics"]["activation_trace"] = list(
                    getattr(ui, "last_activation_trace", []) or []
                )
                report["diagnostics"]["conversation_evidence"] = dict(
                    getattr(ui, "last_conversation_evidence", {}) or {}
                )

        snap = wait(
            ui,
            contact,
            args.draft or "__benchmark__",
            lambda s: identity(s.get("conversation")) == identity(contact)
            and bool(s.get("composer")),
        )
        report["diagnostics"]["conversation_after_activation"] = snap.get("conversation")
        report["diagnostics"]["composer_after_activation"] = snap.get("composer")
        report["diagnostics"]["draft_before"] = snap.get("draft")

        if identity(snap.get("conversation")) != identity(contact):
            raise RuntimeError(
                "Cabeçalho raw da conversa não foi verificado no painel direito."
            )
        if not snap.get("composer"):
            raise RuntimeError(
                "A conversa abriu, mas o compositor não pôde ser focalizado."
            )

        report["steps"].append("conversation_verified")
        report["composer"] = snap.get("composer")
        report["draft_before"] = snap.get("draft")

        if args.draft is not None:
            draft = str(args.draft)
            if snap.get("draft") not in ("", None, draft):
                raise RuntimeError("Existe outro rascunho; foi preservado.")

            composer = choose_text_field(snap["controls"], purpose="message")
            if snap.get("draft") != draft:
                ui.set_text(composer["key"], draft)

            snap = wait(
                ui, contact, draft,
                lambda s: identity(s.get("conversation")) == identity(contact)
                and s.get("draft") == draft,
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
