import re


URL_RE = re.compile(r"https://[^\s)]+", re.I)


def parse_acquisition_command(text):
    raw = str(text or "").strip()
    low = raw.lower()

    if any(x in low for x in (
        "liste lacunas de capacidade", "mostrar lacunas de capacidade",
        "quais capacidades faltam", "lacunas do jarvis",
    )):
        return {"action": "gaps"}

    if any(x in low for x in (
        "liste capacidades candidatas", "candidatos de capacidade",
        "capacidades em descoberta", "o que você está aprendendo sozinho",
        "o que voce esta aprendendo sozinho",
    )):
        return {"action": "candidates"}

    m = re.search(r"(?:instale|instalar|aprove|aprovar)\s+(?:a\s+)?(?:capacidade|compet[eê]ncia|candidato)\s*#?\s*(\d+)", low)
    if m:
        return {"action": "install", "candidate_id": int(m.group(1))}

    m = re.search(r"(?:teste|testar|valide|validar)\s+(?:a\s+)?(?:capacidade|compet[eê]ncia|candidato)\s*#?\s*(\d+)", low)
    if m:
        return {"action": "test", "candidate_id": int(m.group(1))}

    discover_patterns = (
        r"^(?:descubra|descobrir)\s+como\s+(?:fazer|realizar)\s+(.+)$",
        r"^(?:tente descobrir)\s+como\s+(.+)$",
    )
    for pattern in discover_patterns:
        m = re.match(pattern, raw, flags=re.I)
        if m:
            url = URL_RE.search(raw)
            return {
                "action": "discover",
                "goal": m.group(1).strip(),
                "source_url": url.group(0).rstrip(".,;") if url else None,
                "auto_install": False,
            }

    learn_patterns = (
        r"^(?:aprenda|aprender)\s+sozinho\s+(?:a\s+)?(?:fazer|realizar)\s+(.+)$",
        r"^(?:aprenda|aprender)\s+(?:a\s+)?(?:fazer|realizar)\s+(.+?)\s+sozinho$",
        r"^(?:adquira|adquirir)\s+(?:a\s+)?capacidade\s+de\s+(.+)$",
        r"^(?:tente aprender)\s+como\s+(.+)$",
    )
    for pattern in learn_patterns:
        m = re.match(pattern, raw, flags=re.I)
        if m:
            url = URL_RE.search(raw)
            return {
                "action": "discover",
                "goal": m.group(1).strip(),
                "source_url": url.group(0).rstrip(".,;") if url else None,
                "auto_install": True,
            }

    patterns = (
        r"^(?:o que falta para|o que te falta para)\s+(?:você\s+|voce\s+)?(?:fazer|realizar)\s+(.+)$",
        r"^(?:você sabe|voce sabe)\s+(?:como\s+)?(?:fazer|realizar)\s+(.+)\?$",
        r"^(?:tem capacidade para|consegue aprender a)\s+(.+)$",
    )
    for pattern in patterns:
        m = re.match(pattern, raw, flags=re.I)
        if m:
            return {"action": "resolve", "goal": m.group(1).strip()}

    return None
