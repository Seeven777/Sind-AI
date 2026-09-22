import re
import urllib.parse


def _query_url(engine, query):
    q = urllib.parse.quote_plus(str(query).strip())
    if engine == "google":
        return f"https://www.google.com/search?q={q}"
    if engine == "google_images":
        return f"https://www.google.com/search?tbm=isch&q={q}"
    if engine == "youtube":
        return f"https://www.youtube.com/results?search_query={q}"
    if engine == "bing":
        return f"https://www.bing.com/search?q={q}"
    if engine == "duckduckgo":
        return f"https://duckduckgo.com/?q={q}"
    if engine == "google_maps":
        return f"https://www.google.com/maps/search/{urllib.parse.quote(str(query).strip())}"
    return f"https://www.google.com/search?q={q}"


def parse_fast_intent(text):
    """High-confidence compound intents that should never wait for the LLM."""
    t = str(text).strip()

    if re.match(
        r"^\s*(?:oi|ol[aá]|opa|eai|e aí|bom\s+dia|boa\s+tarde|boa\s+noite)"
        r"(?:\s+jarvis)?\s*[.!?]*\s*$",
        t, flags=re.I,
    ):
        return {"kind": "greeting"}

    patterns = [
        ("google_images", r"(?:abra\s+)?(?:o\s+)?google\s+imagens?\s+(?:e\s+)?(?:pesquise|procure|busque)(?:\s+(?:por|sobre))?\s+(.+)$"),
        ("google_maps", r"(?:abra\s+)?(?:o\s+)?google\s+maps\s+(?:e\s+)?(?:pesquise|procure|busque)(?:\s+(?:por|sobre))?\s+(.+)$"),
        ("youtube", r"(?:abra\s+)?(?:o\s+)?youtube\s+(?:e\s+)?(?:pesquise|procure|busque)(?:\s+(?:por|sobre))?\s+(.+)$"),
        ("google", r"(?:abra\s+)?(?:o\s+)?google\s+(?:e\s+)?(?:pesquise|procure|busque)(?:\s+(?:por|sobre))?\s+(.+)$"),
        ("bing", r"(?:abra\s+)?(?:o\s+)?bing\s+(?:e\s+)?(?:pesquise|procure|busque)(?:\s+(?:por|sobre))?\s+(.+)$"),
        ("duckduckgo", r"(?:abra\s+)?(?:o\s+)?duckduckgo\s+(?:e\s+)?(?:pesquise|procure|busque)(?:\s+(?:por|sobre))?\s+(.+)$"),
        ("google", r"(?:pesquise|procure|busque)(?:\s+(?:por|sobre))?\s+(.+?)\s+(?:no|pelo)\s+google$"),
        ("youtube", r"(?:pesquise|procure|busque)(?:\s+(?:por|sobre))?\s+(.+?)\s+(?:no|pelo)\s+youtube$"),
    ]

    for engine, pattern in patterns:
        m = re.match(r"^\s*" + pattern + r"\s*[.!?]*\s*$", t, flags=re.I)
        if m:
            query = m.group(1).strip().strip("\"'").rstrip(" .!?")
            if query:
                return {
                    "kind": "open_search",
                    "engine": engine,
                    "query": query,
                    "url": _query_url(engine, query),
                }



    if re.match(r"^\s*(?:por que|porque|pq)\s+(?:a\s+)?tarefa\s+falhou\??\s*$", t, flags=re.I):
        return {"kind": "diagnose_last_failure"}

    # Pesquisa estruturada com criação de arquivo. Rota deliberadamente
    # determinística para não depender de vários ciclos do modelo local.
    low = t.lower()
    if (
        re.search(r"\b(?:pesquise|procure|busque)\b", low)
        and re.search(r"\b(?:web|internet)\b", low)
        and re.search(r"\b(?:crie|salve|gere)\b", low)
        and re.search(r"\barquivo\b", low)
    ):
        # Tenta extrair o tema entre 'sobre/por' e o primeiro delimitador de tarefa.
        m = re.search(
            r"(?:sobre|por)\s+(.+?)(?=,|\s+e\s+(?:encontre|ache|selecione|crie|salve|gere)|$)",
            t, flags=re.I
        )
        query = (m.group(1) if m else t).strip().strip('\"\'').rstrip(" .!?")
        if query:
            return {"kind": "research_to_file", "query": query}

    # Pesquisa pública que deve retornar resultados dentro do Jarvis.
    m = re.match(
        r"^\s*(?:pesquise|procure|busque)\s+(?:na\s+web|na\s+internet)\s+(?:por|sobre)?\s*(.+?)\s*[.!?]*$",
        t,
        flags=re.I,
    )
    if m:
        return {"kind": "web_search", "query": m.group(1).strip()}

    # Abrir buscadores sem consulta.
    simple = {
        r"^\s*abra\s+(?:o\s+)?google\s*[.!?]*$": "https://www.google.com",
        r"^\s*abra\s+(?:o\s+)?youtube\s*[.!?]*$": "https://www.youtube.com",
        r"^\s*abra\s+(?:o\s+)?google\s+maps\s*[.!?]*$": "https://www.google.com/maps",
    }
    for pattern, url in simple.items():
        if re.match(pattern, t, flags=re.I):
            return {"kind": "open_url", "url": url}

    return None
