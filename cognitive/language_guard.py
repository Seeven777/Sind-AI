import re

# Regra compartilhada pelos runtimes conversacionais.
PORTUGUESE_SYSTEM_RULE = (
    "IDIOMA OBRIGATÓRIO: toda comunicação do Jarvis com o usuário deve ser em "
    "português do Brasil (pt-BR). Não responda em inglês por padrão, mesmo que "
    "fontes, páginas, documentação, nomes de ferramentas ou mensagens internas "
    "estejam em inglês. Preserve apenas código, comandos, URLs, nomes próprios, "
    "nomes técnicos e trechos literais quando necessário. Se receber contexto "
    "em outro idioma, compreenda-o internamente e explique o resultado em pt-BR."
)

_PT_WORDS = {
    "a", "ao", "aos", "as", "com", "como", "da", "das", "de", "do", "dos",
    "e", "ela", "ele", "em", "eu", "isso", "já", "mais", "me", "meu", "minha",
    "não", "nos", "o", "os", "ou", "para", "pela", "pelo", "por", "porque",
    "que", "se", "sem", "seu", "sua", "também", "tem", "uma", "você", "vou",
    "foi", "ser", "está", "estou", "consigo", "posso", "preciso", "tarefa",
    "resposta", "erro", "falha", "ajudar", "agora", "tente", "novamente",
}

_EN_WORDS = {
    "a", "an", "and", "are", "as", "assist", "be", "beginning", "but", "can",
    "could", "do", "error", "encountered", "for", "from", "had", "has", "have",
    "help", "how", "i", "in", "internal", "is", "it", "let", "me", "of", "on",
    "process", "request", "response", "start", "the", "this", "to", "today",
    "try", "was", "we", "what", "while", "with", "you", "your", "again",
}

_EN_PHRASES = (
    "i encountered",
    "how can i",
    "let's try",
    "lets try",
    "your request",
    "internal error",
    "i can help",
    "i'm sorry",
    "i am sorry",
    "please try",
)


def _strip_non_prose(text):
    """Remove regiões que podem legitimamente conter inglês técnico."""
    s = str(text or "")
    s = re.sub(r"```[\s\S]*?```", " ", s)
    s = re.sub(r"`[^`\n]+`", " ", s)
    s = re.sub(r"https?://\S+", " ", s)
    s = re.sub(r"\b[A-Za-z]:\\[^\s]+", " ", s)
    # Remove linhas que parecem comandos, JSON ou stack traces.
    kept = []
    for line in s.splitlines():
        t = line.strip()
        if not t:
            continue
        if t.startswith(("{", "}", "[", "]", "$ ", "> ", "Traceback", "File ")):
            continue
        if re.search(r"\b(import|from|def|class|return|const|let|var|git|python|pip|npm)\b", t) and (
            "=" in t or "(" in t or t.startswith(("git ", "python ", "pip ", "npm "))
        ):
            continue
        kept.append(t)
    return " ".join(kept)


def looks_english_dominant(text):
    """
    Heurística barata para capturar deriva para inglês sem chamar outro modelo
    em respostas que já estão corretas em português.
    """
    prose = _strip_non_prose(text)
    if not prose:
        return False

    low = prose.lower()
    if any(p in low for p in _EN_PHRASES):
        return True

    words = re.findall(r"[a-záàâãéêíóôõúüç']+", low)
    if len(words) < 5:
        return False

    en = sum(1 for w in words if w in _EN_WORDS)
    pt = sum(1 for w in words if w in _PT_WORDS)

    # Só corrige quando há sinal razoavelmente forte de inglês.
    return en >= 4 and en >= (pt + 2) and (en / max(1, len(words))) >= 0.18


def ensure_portuguese_response(text, models, user_text=""):
    """
    Última barreira antes de uma resposta chegar à UI.

    - Não toca em respostas que já parecem pt-BR.
    - Se detectar inglês dominante, pede uma reescrita curta ao modelo FAST.
    - Se a reescrita falhar ou continuar em inglês, devolve uma mensagem segura
      em português em vez de expor uma resposta fora do idioma configurado.
    """
    original = str(text or "").strip()
    if not original or not looks_english_dominant(original):
        return original

    system = (
        PORTUGUESE_SYSTEM_RULE
        + "\nVocê atua somente como revisor de idioma. Reescreva o texto fornecido "
          "em português do Brasil, sem acrescentar fatos, sem resumir informações, "
          "sem alterar comandos, código, URLs, nomes próprios ou valores. "
          "Retorne apenas a versão corrigida."
    )
    prompt = (
        "TEXTO A CORRIGIR:\n"
        f"{original}\n\n"
        "Reescreva integralmente em português do Brasil."
    )

    try:
        response = models.chat(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            user_text=user_text or "corrigir idioma da resposta",
            force="fast",
        )
        candidate = str(((response.get("message") or {}).get("content") or "")).strip()
        candidate = re.sub(r"<think\b[^>]*>.*?</think>", "", candidate, flags=re.I | re.S).strip()
        candidate = re.sub(r"</?think\b[^>]*>", "", candidate, flags=re.I).strip()
        if candidate and not looks_english_dominant(candidate):
            return candidate
    except Exception:
        pass

    return (
        "Ocorreu uma falha ao formular a resposta em português. "
        "Repita a solicitação para eu tentar novamente."
    )
