"""Probe seguro do WhatsApp: abre uma conversa e inspeciona a UIA no mesmo processo.

Não digita mensagem e não envia nada. O único texto escrito é o nome do contato no
campo de pesquisa para localizar a conversa solicitada.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from runtime.phase4.controls import choose_text_field
from runtime.phase4.intent import identity, fold
from runtime.phase4.whatsapp_uia import WhatsAppUIA


def safe_patterns(ctrl):
    names = []
    for attr, label in (
        ("iface_value", "Value"),
        ("iface_text", "Text"),
        ("iface_invoke", "Invoke"),
        ("iface_legacy_iaccessible", "LegacyIAccessible"),
        ("iface_selection_item", "SelectionItem"),
    ):
        try:
            getattr(ctrl, attr)
            names.append(label)
        except Exception:
            pass
    return names


def describe(ctrl, index, wr):
    info = ctrl.element_info
    rect = ctrl.rectangle()
    bounds = [rect.left, rect.top, rect.right, rect.bottom]
    name = str(info.name or "")
    aid = str(info.automation_id or "")
    ctype = str(info.control_type or "")
    try:
        focused = bool(ctrl.has_keyboard_focus())
    except Exception:
        focused = False
    try:
        visible = bool(ctrl.is_visible())
    except Exception:
        visible = False
    try:
        enabled = bool(ctrl.is_enabled())
    except Exception:
        enabled = False

    width = max(1, wr.right - wr.left)
    height = max(1, wr.bottom - wr.top)
    center_x = (rect.left + rect.right) / 2
    center_y = (rect.top + rect.bottom) / 2

    return {
        "key": f"raw:{index}",
        "name": name[:250],
        "automation_id": aid[:180],
        "control_type": ctype,
        "visible": visible,
        "enabled": enabled,
        "focused": focused,
        "bounds": bounds,
        "right_half": center_x >= wr.left + width * 0.48,
        "bottom_third": center_y >= wr.top + height * 0.66,
        "patterns": safe_patterns(ctrl),
    }


def wait_for(predicate, timeout=10.0, poll=0.25):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        last = predicate()
        if last:
            return last
        time.sleep(poll)
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--contact", required=True)
    parser.add_argument(
        "--output",
        default="probe_conversa_aberta.json",
        help="Arquivo JSON UTF-8 de saída.",
    )
    args = parser.parse_args()

    contact = args.contact.strip()
    if not contact:
        raise SystemExit("Contato vazio.")

    ui = WhatsAppUIA()
    result = {
        "ok": False,
        "contact": contact,
        "sent_message": False,
        "typed_message": False,
        "steps": [],
    }

    try:
        ui.open()
        result["steps"].append("WhatsApp conectado")

        def get_search_snapshot():
            snap = ui.observe(contact, "__phase4_probe_only__")
            if not snap.get("ok") or not snap.get("controls"):
                return None
            try:
                search = choose_text_field(snap["controls"], purpose="search")
            except Exception:
                return None
            return snap, search

        pair = wait_for(get_search_snapshot)
        if not pair:
            raise RuntimeError("Campo de pesquisa do WhatsApp não ficou disponível.")
        snap, search = pair

        ui.set_text(search["key"], contact)
        result["steps"].append("Contato escrito somente no campo de pesquisa")

        def get_contact():
            snap = ui.observe(contact, "__phase4_probe_only__")
            if snap.get("search_value") != contact:
                return None
            candidates = [
                x for x in snap.get("contacts", [])
                if identity(x.get("name")) == identity(contact)
            ]
            if len(candidates) == 1:
                return candidates[0]
            return None

        candidate = wait_for(get_contact)
        if not candidate:
            raise RuntimeError(
                "O contato exato não apareceu de forma única na pesquisa."
            )

        ui.open_contact(candidate["key"])
        result["steps"].append("Resultado exato da pesquisa acionado")
        time.sleep(1.0)

        win = ui._attach()
        wr = win.rectangle()
        descendants = win.descendants()

        rows = []
        for index, ctrl in enumerate(descendants[:4000]):
            try:
                row = describe(ctrl, index, wr)
                rect = row["bounds"]
                area = max(0, rect[2] - rect[0]) * max(0, rect[3] - rect[1])
                if area <= 0:
                    continue
                rows.append(row)
            except Exception:
                continue

        contact_hits = [
            row for row in rows
            if identity(row["name"]) == identity(contact)
        ]
        focused = [row for row in rows if row["focused"]]
        edit_like = [
            row for row in rows
            if row["control_type"] in ("Edit", "Document")
            or any(p in row["patterns"] for p in ("Value", "Text"))
        ]
        right_bottom = [
            row for row in rows
            if row["right_half"] and row["bottom_third"]
        ]
        composer_hints = [
            row for row in rows
            if any(token in fold(row["name"] + " " + row["automation_id"])
                   for token in (
                       "mensagem", "message", "compose", "digite",
                       "type a", "editor", "input", "textbox"
                   ))
        ]

        result.update({
            "ok": True,
            "window": dict(ui.window_metadata),
            "window_bounds": [wr.left, wr.top, wr.right, wr.bottom],
            "descendants": len(descendants),
            "exact_contact_hits": contact_hits,
            "focused_controls": focused,
            "edit_or_text_pattern_controls": edit_like,
            "composer_hints": composer_hints,
            "right_bottom_controls": right_bottom[:300],
        })

    except Exception as exc:
        result["error"] = str(exc)

    output = Path(args.output).resolve()
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Probe salvo em UTF-8: {output}")
    print(f"OK: {result.get('ok')}")
    print("Nenhuma mensagem foi digitada ou enviada.")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
