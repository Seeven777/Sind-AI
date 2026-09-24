"""Static/runtime wiring diagnostic for Computer Runtime V2. No UI actions."""
from __future__ import annotations

import inspect
import json
from pathlib import Path

import access.controller as access_controller
import core.agent as core_agent
import core.router as core_router
import runtime.computer_v2 as computer_v2
from runtime.phase4.whatsapp_interactive import parse_whatsapp_interactive


def main():
    command = "abra o WhatsApp\nselecione a conversa Me (você)"
    parsed = parse_whatsapp_interactive(command)
    source = inspect.getsource(core_agent.JarvisAgent._run_internal)
    result = {
        "ok": True,
        "core_agent_file": str(Path(core_agent.__file__).resolve()),
        "controller_file": str(Path(access_controller.__file__).resolve()),
        "computer_v2_file": str(Path(computer_v2.__file__).resolve()),
        "router_fast_path_for_compound": core_router.fast_path(command, Path("C:/Desktop")),
        "interactive_parse": {
            "handled": bool(parsed and parsed.handled),
            "select": bool(parsed and parsed.select),
            "contact": parsed.contact if parsed else "",
            "type_text": bool(parsed and parsed.type_text),
            "send": bool(parsed and parsed.send),
        },
        "early_route_marker_loaded": "COMPUTER_RUNTIME_V2_EARLY_WHATSAPP" in source,
    }
    result["ok"] = bool(
        result["router_fast_path_for_compound"] is None
        and result["interactive_parse"]["select"]
        and result["interactive_parse"]["contact"] == "Me (você)"
        and result["early_route_marker_loaded"]
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["ok"]:
        print("\nO processo/arquivo carregado ainda não está usando o wiring do Computer Runtime V2.")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
