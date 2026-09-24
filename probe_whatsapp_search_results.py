"""Diagnóstico somente-leitura dos resultados da busca do WhatsApp Desktop.

O script escreve apenas o nome do contato no campo de pesquisa. Não abre conversa,
não digita mensagem no chat e não envia nada.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from runtime.phase4.controls import choose_text_field
from runtime.phase4.intent import identity, fold
from runtime.phase4.whatsapp_uia import WhatsAppUIA


def pattern_names(ctrl):
    out = []
    for attr, label in (
        ("iface_value", "Value"),
        ("iface_text", "Text"),
        ("iface_invoke", "Invoke"),
        ("iface_legacy_iaccessible", "LegacyIAccessible"),
        ("iface_selection_item", "SelectionItem"),
    ):
        try:
            getattr(ctrl, attr)
            out.append(label)
        except Exception:
            pass
    return out


def parent_chain(ctrl, limit=5):
    result = []
    current = ctrl
    for _ in range(limit):
        try:
            parent = current.parent()
            if parent is None or parent == current:
                break
            info = parent.element_info
            rect = parent.rectangle()
            result.append({
                "name": str(info.name or "")[:180],
                "automation_id": str(info.automation_id or "")[:120],
                "control_type": str(info.control_type or ""),
                "bounds": [rect.left, rect.top, rect.right, rect.bottom],
            })
            current = parent
        except Exception:
            break
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--contact", required=True)
    parser.add_argument("--output", default="probe_resultados_busca.json")
    args = parser.parse_args()

    contact = args.contact.strip()
    ui = WhatsAppUIA()
    result = {
        "ok": False,
        "contact": contact,
        "sent_message": False,
        "typed_message": False,
        "opened_conversation": False,
        "steps": [],
    }

    try:
        ui.open()
        result["steps"].append("WhatsApp conectado")

        deadline = time.monotonic() + 8
        snap = None
        search = None
        while time.monotonic() < deadline:
            snap = ui.observe(contact, "__probe_only__")
            if snap.get("ok") and snap.get("controls"):
                try:
                    search = choose_text_field(snap["controls"], purpose="search")
                    break
                except Exception:
                    pass
            time.sleep(.2)
        if not search:
            raise RuntimeError("Campo de pesquisa não ficou disponível.")

        ui.set_text(search["key"], contact)
        result["steps"].append("Contato escrito somente no campo de pesquisa")

        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            snap = ui.observe(contact, "__probe_only__")
            if snap.get("search_value") == contact:
                break
            time.sleep(.2)

        win = ui._attach()
        wr = win.rectangle()
        descendants = win.descendants()

        search_bounds = search.get("bounds") or [wr.left, wr.top, wr.left + 350, wr.top + 100]
        left_limit = max(search_bounds[2] + 120, wr.left + int((wr.right - wr.left) * .45))
        top_limit = search_bounds[3] - 5

        rows = []
        exact = []
        contains = []

        for idx, ctrl in enumerate(descendants[:4000]):
            try:
                info = ctrl.element_info
                rect = ctrl.rectangle()
                if rect.right <= rect.left or rect.bottom <= rect.top:
                    continue
                if rect.left > left_limit:
                    continue
                if rect.bottom < top_limit:
                    continue

                name = str(info.name or "")
                aid = str(info.automation_id or "")
                ctype = str(info.control_type or "")

                row = {
                    "key": f"raw:{idx}",
                    "name": name[:300],
                    "automation_id": aid[:180],
                    "control_type": ctype,
                    "visible": bool(ctrl.is_visible()),
                    "enabled": bool(ctrl.is_enabled()),
                    "bounds": [rect.left, rect.top, rect.right, rect.bottom],
                    "patterns": pattern_names(ctrl),
                    "parents": parent_chain(ctrl),
                }
                rows.append(row)

                if identity(name) == identity(contact):
                    exact.append(row)
                elif identity(contact) in identity(name) or identity(name) in identity(contact):
                    if name.strip():
                        contains.append(row)
            except Exception:
                continue

        result.update({
            "ok": True,
            "window_bounds": [wr.left, wr.top, wr.right, wr.bottom],
            "search_bounds": search_bounds,
            "search_value": snap.get("search_value") if snap else None,
            "adapter_contacts": snap.get("contacts", []) if snap else [],
            "exact_name_matches": exact,
            "contains_name_matches": contains,
            "search_panel_controls": rows[:350],
            "descendants": len(descendants),
        })

    except Exception as exc:
        result["error"] = str(exc)

    output = Path(args.output).resolve()
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Probe salvo em UTF-8: {output}")
    print(f"OK: {result.get('ok')}")
    print("Nenhuma conversa foi aberta; nenhuma mensagem foi digitada ou enviada.")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
