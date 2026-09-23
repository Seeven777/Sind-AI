from pathlib import Path

from core.ollama_client import sanitize_assistant_content
from core.router import fast_path

BASE = Path(__file__).resolve().parent


def check(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name}: {detail}")
    print("[OK]", name)


def main():
    leaked = """Okay, the user asked if I can open WhatsApp.
First I should inspect tools and permissions.
Wait, maybe I should try open_app.
</think>

Posso tentar abrir o WhatsApp no computador host."""
    cleaned = sanitize_assistant_content(leaked)
    check("Chain-of-thought removed", "Okay, the user" not in cleaned, cleaned)
    check("Final answer preserved", cleaned.startswith("Posso tentar"), cleaned)
    check("Think tags removed", "<think" not in cleaned.lower() and "</think>" not in cleaned.lower(), cleaned)

    fully_wrapped = "<think>raciocínio interno secreto</think>Resposta final."
    check("Wrapped think removed", sanitize_assistant_content(fully_wrapped) == "Resposta final.")

    unclosed = "<think>raciocínio ainda não terminou"
    check("Unclosed think never leaks", sanitize_assistant_content(unclosed) == "")

    route = fast_path("Consegue abrir o aplicativo do WhatsApp?", Path.home() / "Desktop")
    check("WhatsApp Fast Path", route == ("open_app", {"app": "whatsapp"}), route)

    css = (BASE/"ui/web/styles.css").read_text(encoding="utf-8")
    check("Grid scroll fix", "grid-template-rows:58px minmax(0,1fr) auto" in css)
    check("Visible chat scrollbar", ".chat-scroll::-webkit-scrollbar" in css)
    check("Jump-bottom control style", ".jump-bottom{" in css)

    html = (BASE/"ui/web/index.html").read_text(encoding="utf-8")
    check("Chat is focusable", 'id="chatScroll" tabindex="0"' in html)
    check("Jump-bottom control exists", 'id="jumpBottomBtn"' in html)

    js = (BASE/"ui/web/app.js").read_text(encoding="utf-8")
    check("Wheel fallback exists", "addEventListener('wheel'" in js)
    check("PageUp/PageDown navigation", "PageDown" in js and "PageUp" in js)
    check("Old stored think sanitized in UI", "cleanAssistantText" in js)

    print("\nUX Stability test concluído.")


if __name__ == "__main__":
    main()
