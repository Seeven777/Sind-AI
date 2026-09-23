import re


def parse_experience_command(text):
    raw=str(text or "").strip()
    low=raw.lower()

    if any(x in low for x in (
        "o que você aprendeu recentemente","o que voce aprendeu recentemente",
        "retrospectiva de aprendizado","retrospectiva do aprendizado",
        "resumo do aprendizado","como você está aprendendo","como voce esta aprendendo",
    )):
        return {"action":"retrospective"}

    if any(x in low for x in (
        "mapa de competências","mapa de competencias","competências aprendidas",
        "competencias aprendidas","onde você está melhor","onde voce esta melhor",
    )):
        return {"action":"competence_map"}

    if any(x in low for x in (
        "reverta a última adaptação","reverta a ultima adaptacao",
        "desfaça a última adaptação","desfaca a ultima adaptacao",
        "rollback da última adaptação","rollback da ultima adaptacao",
    )):
        return {"action":"rollback_last_rule"}

    if any(x in low for x in (
        "liste adaptações","listar adaptações","adaptacoes pendentes",
        "melhorias pendentes das rotinas","evoluções pendentes","evolucoes pendentes",
    )):
        return {"action":"list_candidates"}

    m=re.search(r"(?:aprove|aprovar|instale|instalar)\s+(?:a\s+)?(?:adaptação|adaptacao|melhoria)\s*#?\s*(\d+)",low)
    if m:
        return {"action":"approve_candidate","id":int(m.group(1))}

    m=re.search(r"(?:rejeite|rejeitar|recuse)\s+(?:a\s+)?(?:adaptação|adaptacao|melhoria)\s*#?\s*(\d+)",low)
    if m:
        return {"action":"reject_candidate","id":int(m.group(1))}

    m=re.search(r"(?:transforme|transformar|converta|converter)\s+(?:o\s+)?job\s*#?\s*(\d+)\s+(?:em|numa|em uma)\s+(?:rotina|playbook)",low)
    if m:
        return {"action":"job_to_playbook","job_id":int(m.group(1))}

    if any(x in low for x in (
        "isso funcionou","deu certo","perfeito, funcionou","essa rotina funcionou",
        "isso não funcionou","isso nao funcionou","deu errado","não deu certo","nao deu certo",
        "da próxima vez","da proxima vez","prefiro","não faça","nao faca","evite",
    )):
        return {"action":"feedback","text":raw}

    return None
