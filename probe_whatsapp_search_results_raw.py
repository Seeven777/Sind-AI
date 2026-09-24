"""Raw UIA probe for WhatsApp search results.

This diagnostic intentionally bypasses the Jarvis text-field selector.
It writes only the requested contact name into WhatsApp's search field.
It does not open a conversation, type a chat message, or send anything.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from runtime.phase4.intent import fold, identity
from runtime.phase4.whatsapp_uia import WhatsAppUIA


def ensure_utf8():
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def safe_bool(fn, default=False):
    try:
        return bool(fn())
    except Exception:
        return default


def patterns(ctrl):
    result = []
    for attr, label in (
        ("iface_value", "Value"),
        ("iface_text", "Text"),
        ("iface_invoke", "Invoke"),
        ("iface_legacy_iaccessible", "LegacyIAccessible"),
        ("iface_selection_item", "SelectionItem"),
    ):
        try:
            getattr(ctrl, attr)
            result.append(label)
        except Exception:
            pass
    return result


def describe(ctrl, idx):
    info = ctrl.element_info
    rect = ctrl.rectangle()
    return {
        "key": f"raw:{idx}",
        "name": str(info.name or "")[:320],
        "automation_id": str(info.automation_id or "")[:200],
        "control_type": str(info.control_type or ""),
        "visible": safe_bool(ctrl.is_visible),
        "enabled": safe_bool(ctrl.is_enabled),
        "focused": safe_bool(ctrl.has_keyboard_focus),
        "bounds": [rect.left, rect.top, rect.right, rect.bottom],
        "patterns": patterns(ctrl),
    }


def parent_chain(ctrl, limit=6):
    rows = []
    current = ctrl
    for _ in range(limit):
        try:
            parent = current.parent()
            if parent is None or parent == current:
                break
            info = parent.element_info
            rect = parent.rectangle()
            rows.append({
                "name": str(info.name or "")[:220],
                "automation_id": str(info.automation_id or "")[:160],
                "control_type": str(info.control_type or ""),
                "bounds": [rect.left, rect.top, rect.right, rect.bottom],
                "patterns": patterns(parent),
            })
            current = parent
        except Exception:
            break
    return rows


def raw_descendants(win):
    return win.descendants()


def find_search_control(descendants):
    candidates = []
    for idx, ctrl in enumerate(descendants[:4000]):
        try:
            info = ctrl.element_info
            ctype = str(info.control_type or "")
            name = str(info.name or "")
            aid = str(info.automation_id or "")
            label = fold(name + " " + aid)
            if ctype != "Edit":
                continue

            score = 0
            if "pesquisar" in label or "search" in label:
                score += 200
            if "nova conversa" in label or "new chat" in label:
                score += 80

            rect = ctrl.rectangle()
            if rect.right <= rect.left or rect.bottom <= rect.top:
                continue

            if safe_bool(ctrl.is_enabled):
                score += 20
            if safe_bool(ctrl.is_visible):
                score += 10

            try:
                value = ctrl.iface_value
                read_only = bool(value.CurrentIsReadOnly)
                if not read_only:
                    score += 80
            except Exception:
                read_only = None

            candidates.append((score, idx, ctrl, {
                "name": name,
                "automation_id": aid,
                "bounds": [rect.left, rect.top, rect.right, rect.bottom],
                "read_only": read_only,
            }))
        except Exception:
            continue

    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates


def set_search_value(ctrl, text):
    # Prefer ValuePattern: no clipboard, no global keyboard injection.
    try:
        ctrl.set_focus()
    except Exception:
        pass
    try:
        value = ctrl.iface_value
        if bool(value.CurrentIsReadOnly):
            raise RuntimeError("O campo de pesquisa está read-only.")
        value.SetValue(str(text))
        return "ValuePattern"
    except Exception as first:
        # pywinauto's set_edit_text is still scoped to the selected Edit control.
        try:
            ctrl.set_edit_text(str(text))
            return "set_edit_text"
        except Exception as second:
            raise RuntimeError(
                f"Não consegui escrever no Edit de pesquisa. "
                f"ValuePattern={first}; set_edit_text={second}"
            )


def read_search_value(ctrl):
    try:
        return str(ctrl.iface_value.CurrentValue)
    except Exception:
        try:
            return str(ctrl.window_text() or "")
        except Exception:
            return None


def main():
    ensure_utf8()
    parser = argparse.ArgumentParser()
    parser.add_argument("--contact", required=True)
    parser.add_argument("--output", default="probe_resultados_busca_raw.json")
    args = parser.parse_args()

    contact = str(args.contact).strip()
    output = Path(args.output).resolve()

    result = {
        "ok": False,
        "contact": contact,
        "opened_conversation": False,
        "typed_message": False,
        "sent_message": False,
        "steps": [],
    }

    try:
        ui = WhatsAppUIA()

        # Attach directly to the already-running UIA-rich WhatsApp HWND.
        win = ui._attach()
        result["steps"].append("Janela UIA do WhatsApp conectada")

        try:
            win.set_focus()
        except Exception:
            pass
        time.sleep(.35)

        descendants = raw_descendants(win)
        result["initial_descendants"] = len(descendants)

        candidates = find_search_control(descendants)
        result["raw_search_candidates"] = [
            {
                "score": score,
                "index": idx,
                **meta,
            }
            for score, idx, _ctrl, meta in candidates[:10]
        ]

        if not candidates or candidates[0][0] <= 0:
            # Save a compact list of all Edit nodes before failing.
            edits = []
            for idx, ctrl in enumerate(descendants[:4000]):
                try:
                    if str(ctrl.element_info.control_type or "") == "Edit":
                        edits.append(describe(ctrl, idx))
                except Exception:
                    pass
            result["all_edit_controls"] = edits
            raise RuntimeError(
                "Nenhum Edit de pesquisa reconhecível foi encontrado no raw UIA."
            )

        _, search_index, search_ctrl, search_meta = candidates[0]
        result["chosen_search"] = {
            "index": search_index,
            **search_meta,
        }

        method = set_search_value(search_ctrl, contact)
        result["write_method"] = method
        result["steps"].append("Contato escrito somente no campo de pesquisa")

        deadline = time.monotonic() + 5.0
        observed_value = None
        while time.monotonic() < deadline:
            observed_value = read_search_value(search_ctrl)
            if observed_value == contact:
                break
            time.sleep(.15)
        result["search_value"] = observed_value

        # Let WebView2 update the result list.
        time.sleep(.7)

        win = ui._attach()
        descendants = raw_descendants(win)
        result["post_search_descendants"] = len(descendants)

        wr = win.rectangle()
        sb = search_meta["bounds"]
        search_left, search_top, search_right, search_bottom = sb

        # The result pane is the left side below the search box.
        left_panel_right = max(
            search_right + 180,
            wr.left + int((wr.right - wr.left) * 0.48),
        )

        rows = []
        exact = []
        contains = []

        for idx, ctrl in enumerate(descendants[:4000]):
            try:
                row = describe(ctrl, idx)
                l, t, r, b = row["bounds"]
                if r <= l or b <= t:
                    continue
                if l > left_panel_right:
                    continue
                if b < search_bottom - 5:
                    continue

                row["parents"] = parent_chain(ctrl)
                rows.append(row)

                name = row["name"]
                if name and identity(name) == identity(contact):
                    exact.append(row)
                elif name:
                    n = identity(name)
                    c = identity(contact)
                    if c in n or n in c:
                        contains.append(row)
            except Exception:
                continue

        result.update({
            "ok": True,
            "window": dict(ui.window_metadata),
            "window_bounds": [wr.left, wr.top, wr.right, wr.bottom],
            "search_panel_right": left_panel_right,
            "exact_name_matches": exact,
            "contains_name_matches": contains,
            "search_panel_controls": rows[:500],
        })

    except Exception as exc:
        result["error"] = str(exc)

    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Probe salvo em UTF-8: {output}")
    print(f"OK: {result.get('ok')}")
    print("Nenhuma conversa foi aberta; nenhuma mensagem de chat foi digitada ou enviada.")
    if result.get("error"):
        print("Erro:", result["error"])
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
