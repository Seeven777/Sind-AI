import re
import webbrowser

def open_url(url):
    url = str(url).strip()
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url):
        url = "https://" + url
    ok = webbrowser.open(url, new=2)
    return {"ok": bool(ok), "url": url, "error": None if ok else "Falha ao abrir URL."}
