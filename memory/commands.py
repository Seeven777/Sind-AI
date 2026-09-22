import re


def parse_memory_command(text):
    t = str(text).strip()

    # "quando eu disser pasta do trabalho, quero dizer D:\Trabalho"
    m = re.match(
        r"^\s*quando\s+eu\s+disser\s+(.+?)\s*,?\s*(?:quero\s+dizer|significa|é|eh)\s+(.+?)\s*$",
        t,
        flags=re.I,
    )
    if m:
        return {
            "action": "alias",
            "alias": m.group(1).strip().strip('"').strip("'"),
            "target": m.group(2).strip().strip('"').strip("'"),
        }

    # "lembre que ..."
    m = re.match(r"^\s*(?:lembre|lembre-se)\s+que\s+(.+?)\s*$", t, flags=re.I)
    if m:
        value = m.group(1).strip()
        return {"action": "remember", "value": value}

    # "esqueça ..."
    m = re.match(r"^\s*(?:esqueça|esqueca)\s+(?:que\s+)?(.+?)\s*$", t, flags=re.I)
    if m:
        query = m.group(1).strip().rstrip(" .!?;,:")
        return {"action": "forget", "query": query}

    # listar tudo
    if re.match(
        r"^\s*(?:liste|mostre|quais\s+são|quais\s+sao)\s+(?:as\s+)?(?:suas\s+)?mem[oó]rias\b",
        t,
        flags=re.I,
    ):
        return {"action": "list"}

    # "o que você lembra sobre X?"
    m = re.match(
        r"^\s*o\s+que\s+voc[eê]\s+lembra\s+(?:sobre|de)\s+(.+?)\??\s*$",
        t,
        flags=re.I,
    )
    if m:
        query = m.group(1).strip().rstrip(" .!?;,:")
        return {"action": "recall", "query": query}

    return None
