from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
AGENT = ROOT / "core" / "agent.py"
ANSWER = ROOT / "cognitive" / "answer_engine.py"


def replace_once(text, old, new, label):
    if new in text:
        return text, False
    if old not in text:
        raise RuntimeError(f"Não encontrei o ponto esperado para {label}. O arquivo pode ter mudado.")
    return text.replace(old, new, 1), True


def patch_agent():
    text = AGENT.read_text(encoding="utf-8")
    changed = False

    import_old = "from cognitive.self_awareness import SelfAwareness\n"
    import_new = (
        "from cognitive.self_awareness import SelfAwareness\n"
        "from cognitive.language_guard import ensure_portuguese_response\n"
    )
    text, c = replace_once(text, import_old, import_new, "import do Language Guard")
    changed |= c

    prompt_old = (
        "Converse naturalmente em português e mantenha continuidade. "
        "Entenda o objetivo e decida sozinho se deve responder, pesquisar, consultar conhecimento ou agir."
    )
    prompt_new = (
        "IDIOMA OBRIGATÓRIO: toda comunicação com o usuário deve ser em português do Brasil (pt-BR). "
        "Nunca responda em inglês por padrão, mesmo que fontes, documentação, ferramentas ou contexto estejam em inglês. "
        "Preserve em outro idioma apenas código, comandos, URLs, nomes próprios, termos técnicos inevitáveis e trechos literais quando necessário. "
        "Mantenha continuidade. Entenda o objetivo e decida sozinho se deve responder, pesquisar, consultar conhecimento ou agir."
    )
    text, c = replace_once(text, prompt_old, prompt_new, "regra pt-BR no prompt principal")
    changed |= c

    run_old = (
        "            answer = self._run_internal(user_text, status=status, confirm_callback=confirm_callback)\n"
        "            self.conversations.append(\"user\", user_text)\n"
    )
    run_new = (
        "            answer = self._run_internal(user_text, status=status, confirm_callback=confirm_callback)\n"
        "            # Barreira central de idioma: todos os caminhos públicos passam por aqui.\n"
        "            answer = ensure_portuguese_response(answer, self.models, user_text=user_text)\n"
        "            self.conversations.append(\"user\", user_text)\n"
    )
    text, c = replace_once(text, run_old, run_new, "barreira central de idioma")
    changed |= c

    if changed:
        AGENT.write_text(text, encoding="utf-8")
    return changed


def patch_answer_engine():
    text = ANSWER.read_text(encoding="utf-8")
    changed = False

    old = (
        '            "Você é Jarvis, um GPT pessoal local. Responda naturalmente em português, "\n'
        '            "com continuidade de conversa. Não mencione infraestrutura técnica sem necessidade. "\n'
    )
    new = (
        '            "Você é Jarvis, um GPT pessoal local. IDIOMA OBRIGATÓRIO: responda sempre em português do Brasil (pt-BR). "\n'
        '            "Nunca responda em inglês por padrão, mesmo quando fontes ou contexto estiverem em inglês. "\n'
        '            "Preserve apenas código, comandos, URLs, nomes próprios e termos técnicos quando necessário. "\n'
        '            "Mantenha continuidade de conversa. Não mencione infraestrutura técnica sem necessidade. "\n'
    )
    text, c = replace_once(text, old, new, "regra pt-BR no ConversationalAnswerEngine")
    changed |= c

    if changed:
        ANSWER.write_text(text, encoding="utf-8")
    return changed


def main():
    if not AGENT.exists() or not ANSWER.exists():
        raise SystemExit(
            "Execute este script a partir da raiz do repositório Sind-AI. "
            "Não encontrei core/agent.py e cognitive/answer_engine.py."
        )
    a = patch_agent()
    b = patch_answer_engine()
    print("Language Lock pt-BR aplicado.")
    print(f"core/agent.py: {'alterado' if a else 'já estava atualizado'}")
    print(f"cognitive/answer_engine.py: {'alterado' if b else 'já estava atualizado'}")
    print("Pode executar novamente sem duplicar alterações.")


if __name__ == "__main__":
    main()
