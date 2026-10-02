"""Deterministic multi-turn WhatsApp Desktop interaction for Phase 4.

This layer handles explicit UI commands that are smaller than a full
"send message to contact" goal, for example:

    abra o WhatsApp e selecione a conversa Me (você)
    escreva "teste" no campo de mensagem, mas não envie
    envie a mensagem

State is only a convenience hint. Every mutating step is re-verified against the
current WhatsApp UI before it is allowed to continue.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass

from .controls import choose_text_field
from .intent import fold, identity
from .whatsapp import verify_message


_SEND_WORDS = r"(?:envie|enviar|envia|mande|mandar|manda)"
_TYPE_WORDS = r"(?:escreva|escrever|escreve|digite|digitar|insira|inserir|preencha|preencher)"
_SELECT_WORDS = r"(?:selecione|selecionar|abra|abrir|acesse|acessar)"


@dataclass(frozen=True)
class InteractiveWhatsAppIntent:
    select: bool = False
    contact: str = ""
    type_text: bool = False
    message: str = ""
    send: bool = False
    open_requested: bool = False

    @property
    def handled(self):
        return self.select or self.type_text or self.send


def _strip_quotes(value):
    value = str(value or "").strip()
    if len(value) >= 2 and value[0] in ('"', "'", '“') and value[-1] in ('"', "'", '”'):
        return value[1:-1]
    return value


def _remove_negated_send(text):
    """Remove only locally negated send actions from normalized text."""
    out = re.sub(r"\bnao\s+" + _SEND_WORDS + r"\b", " ", text)
    out = re.sub(r"\bsem\s+(?:enviar|mandar)\b", " ", out)
    return re.sub(r"\s+", " ", out).strip()


def _extract_contact(raw):
    # Stop before a following action clause instead of swallowing it into the name.
    pattern = (
        r"\b" + _SELECT_WORDS +
        r"\s+(?:a\s+)?(?:conversa|chat|contato)\s+(.+?)"
        r"(?=$|\n|\s+(?:e\s+)?(?:" + _TYPE_WORDS[3:-1] + r"|envie|mande|nao\s+envie)\b)"
    )
    m = re.search(pattern, raw, flags=re.I | re.S)
    if not m:
        return ""
    contact = m.group(1).strip().rstrip(".,;:")
    # Keep parentheses in real contact labels such as "Me (você)".
    if not contact or "\n" in contact:
        return ""
    return contact


def _extract_message(raw):
    # Form 1: escreva "texto" no campo de mensagem
    m = re.search(
        r"\b" + _TYPE_WORDS + r"\s+[\"“'](.+?)[\"”'](?:\s|$)",
        raw,
        flags=re.I | re.S,
    )
    if m:
        return m.group(1)

    # Form 2: escreva no chat aberto do WhatsApp: "texto"
    m = re.search(
        r"\b" + _TYPE_WORDS +
        r"\s+(?:(?:no|na)\s+)?(?:chat|conversa|campo(?:\s+de\s+mensagem)?|caixa\s+de\s+mensagem)"
        r"(?:\s+abert[oa])?(?:\s+do\s+whats\s*app)?\s*:\s*[\"“'](.+?)[\"”']\s*$",
        raw,
        flags=re.I | re.S,
    )
    if m:
        return m.group(1)

    # Form 3: same contextual syntax without quotes. Keep it conservative and
    # only accept text after an explicit colon.
    m = re.search(
        r"\b" + _TYPE_WORDS +
        r"\s+(?:(?:no|na)\s+)?(?:chat|conversa|campo(?:\s+de\s+mensagem)?|caixa\s+de\s+mensagem)"
        r"(?:\s+abert[oa])?(?:\s+do\s+whats\s*app)?\s*:\s*(.+?)\s*$",
        raw,
        flags=re.I | re.S,
    )
    if m:
        return _strip_quotes(m.group(1).strip())

    return ""


def parse_whatsapp_interactive(text, state=None):
    """Parse explicit partial WhatsApp commands.

    Full atomic commands such as ``Envie no WhatsApp para Maria: Olá`` are not
    consumed here; the existing Phase 4 full-send executor keeps precedence.
    """
    raw = str(text or "").strip()
    if not raw:
        return None

    t = fold(raw)
    state = state or {}
    state_contact = str(state.get("contact") or "").strip()

    # Pure informational questions must never become physical interaction.
    if re.match(r"^(?:como\b|o que\b|qual\b|quais\b|por que\b|explique\b|me explique\b|ensine\b|me ensine\b)", t):
        return None

    whatsapp_mentioned = bool(re.search(r"\bwhats\s*app\b", t))
    contextual_chat = bool(re.search(
        r"\b(?:campo de mensagem|caixa de mensagem|chat abert[oa]|conversa abert[oa]|chat selecionad[oa]|conversa selecionad[oa])\b",
        t,
    ))

    contact = _extract_contact(raw)
    message = _extract_message(raw)

    open_requested = whatsapp_mentioned and bool(re.search(r"\b(?:abra|abrir|abre|inicie|iniciar)\b", t))
    select = bool(contact)
    type_text = bool(message)

    positive = _remove_negated_send(t)
    # Only a genuinely positive send clause authorizes sending. "não envie" is
    # removed above, while a later "envie a mensagem" remains.
    send = bool(re.search(
        r"\b(?:envie|mande)(?:\s+(?:agora|a\s+mensagem|essa\s+mensagem|o\s+texto))?\b",
        positive,
    ))

    # Do not steal the full-send syntax; that path requires recipient+payload in
    # the same command and has its own stricter parser/verifier.
    if re.search(r"\b(?:envie|mande)\b.*\b(?:para|pro|pra|ao|a)\s+[^:\n]+:\s*.+$", raw, flags=re.I | re.S):
        return None

    # "envie a mensagem" may omit the word WhatsApp only as a continuation of
    # a verified state from an earlier turn.
    continuation = bool(state_contact)
    if not (whatsapp_mentioned or contextual_chat or select or continuation):
        return None

    # A bare "abra o WhatsApp" remains on the existing fast path. This layer is
    # for the remaining interaction, not for replacing a working open-only path.
    if not (select or type_text or send):
        return None

    # Typing without a known/selected chat is handled, but the executor will fail
    # closed with a clear request to select a conversation first.
    return InteractiveWhatsAppIntent(
        select=select,
        contact=contact,
        type_text=type_text,
        message=message,
        send=send,
        open_requested=open_requested,
    )


class WhatsAppInteractiveExecutor:
    """Observe -> act -> observe -> verify for partial WhatsApp commands."""

    def __init__(self, adapter, timeout=12, poll=0.25, cancelled=None, event=None):
        self.ui = adapter
        self.timeout = max(0.01, min(float(timeout), 30))
        self.poll = float(poll)
        self.cancelled = cancelled or (lambda: None)
        self.event = event or (lambda *args: None)
        self.events = []
        self.send_attempted = False

    def emit(self, item):
        self.events.append(item)
        try:
            self.event(item)
        except Exception:
            pass

    def observe(self, contact, message="__jarvis_phase4_probe__"):
        self.cancelled()
        snap = self.ui.observe(contact, message)
        self.emit({
            "phase": "observe",
            "ok": bool(snap.get("ok")),
            "conversation": snap.get("conversation"),
            "complete": snap.get("complete"),
            "draft_chars": len(snap.get("draft") or ""),
        })
        return snap

    def wait(self, contact, message, predicate, reason):
        deadline = time.monotonic() + self.timeout
        while True:
            snap = self.observe(contact, message)
            if snap.get("ok") and predicate(snap):
                return snap
            if time.monotonic() >= deadline:
                raise RuntimeError(reason)
            time.sleep(self.poll)

    def act(self, name, *args):
        self.cancelled()
        self.emit({"phase": "act", "action": name})
        return getattr(self.ui, name)(*args)

    def select_conversation(self, contact):
        try:
            if not contact:
                raise RuntimeError("Informe o nome exato da conversa que deve ser aberta.")
            self.observe(contact)
            self.act("open")
            snap = self.wait(
                contact,
                "__jarvis_phase4_probe__",
                lambda s: bool(s.get("controls")),
                "WhatsApp Desktop não ficou acessível via UI Automation.",
            )
            search = choose_text_field(snap["controls"], purpose="search")
            self.act("set_text", search["key"], contact)
            snap = self.wait(
                contact,
                "__jarvis_phase4_probe__",
                lambda s: s.get("search_value") == contact and bool(s.get("contacts")),
                "Contato exato não apareceu na pesquisa do WhatsApp.",
            )
            candidates = [x for x in snap.get("contacts", []) if identity(x.get("name")) == identity(contact)]
            if len(candidates) != 1:
                raise RuntimeError("Contato ausente ou ambíguo. Use o nome único exibido no WhatsApp.")
            self.act("open_contact", candidates[0]["key"])
            snap = self.wait(
                contact,
                "__jarvis_phase4_probe__",
                lambda s: identity(s.get("conversation")) == identity(contact) and bool(s.get("composer")),
                "Não confirmei o cabeçalho e o campo de mensagem da conversa solicitada.",
            )
            verification = {
                "verified": True,
                "scope": "goal",
                "reason": "Conversa solicitada observada no cabeçalho e compositor acessível.",
                "conversation": contact,
            }
            self.emit({"phase": "verify", **verification})
            return {
                "ok": True,
                "status": "verified",
                "goal_verification": verification,
                "contact": contact,
                "draft": snap.get("draft"),
                "events": self.events,
            }
        except Exception as exc:
            reason = str(exc) or type(exc).__name__
            verification = {"verified": False, "scope": "goal", "reason": reason}
            self.emit({"phase": "verify", **verification})
            return {"ok": False, "status": "failed", "error": reason,
                    "goal_verification": verification, "events": self.events}

    def type_draft(self, contact, message):
        try:
            if not contact:
                raise RuntimeError("Nenhuma conversa do WhatsApp foi selecionada pelo Jarvis. Selecione a conversa primeiro.")
            if message == "":
                raise RuntimeError("Informe o texto literal que deve ser digitado.")
            self.act("open")
            snap = self.wait(
                contact,
                message,
                lambda s: identity(s.get("conversation")) == identity(contact) and bool(s.get("composer")),
                "A conversa verificada anteriormente não está mais aberta no WhatsApp.",
            )
            draft = snap.get("draft")
            if draft is None:
                raise RuntimeError("Não consegui ler o campo de mensagem; nenhuma escrita foi feita.")
            if draft not in ("", message):
                raise RuntimeError("Já existe outro rascunho nessa conversa. Ele foi preservado; limpe-o ou envie-o antes de substituir.")
            if draft != message:
                composer = choose_text_field(snap["controls"], purpose="message")
                self.act("set_text", composer["key"], message)
            snap = self.wait(
                contact,
                message,
                lambda s: identity(s.get("conversation")) == identity(contact) and s.get("draft") == message,
                "Não consegui reler o texto exato no campo de mensagem.",
            )
            verification = {
                "verified": True,
                "scope": "goal",
                "reason": "Texto literal relido no compositor da conversa correta; envio não executado.",
                "conversation": contact,
            }
            self.emit({"phase": "verify", **verification})
            return {"ok": True, "status": "verified", "goal_verification": verification,
                    "contact": contact, "draft": message, "events": self.events}
        except Exception as exc:
            reason = str(exc) or type(exc).__name__
            verification = {"verified": False, "scope": "goal", "reason": reason}
            self.emit({"phase": "verify", **verification})
            return {"ok": False, "status": "failed", "error": reason,
                    "goal_verification": verification, "events": self.events}

    def read_current_draft(self, contact):
        try:
            if not contact:
                raise RuntimeError("Nenhuma conversa do WhatsApp foi selecionada pelo Jarvis.")
            self.act("open")
            snap = self.wait(
                contact,
                "__jarvis_phase4_probe__",
                lambda s: identity(s.get("conversation")) == identity(contact) and bool(s.get("composer")),
                "A conversa verificada anteriormente não está mais aberta no WhatsApp.",
            )
            if snap.get("draft") is None:
                raise RuntimeError("Não consegui ler o rascunho atual do campo de mensagem.")
            return {"ok": True, "contact": contact, "draft": snap.get("draft"), "snapshot": snap}
        except Exception as exc:
            return {"ok": False, "error": str(exc) or type(exc).__name__}

    def send_current(self, contact, message, confirm=None, require_confirmation=True):
        tool_ok = False
        try:
            if not contact:
                raise RuntimeError("Nenhuma conversa do WhatsApp foi selecionada pelo Jarvis.")
            if not message:
                raise RuntimeError("O campo de mensagem está vazio; nada foi enviado.")

            self.act("open")
            before = self.wait(
                contact,
                message,
                lambda s: identity(s.get("conversation")) == identity(contact) and s.get("draft") == message,
                "A conversa ou o rascunho atual não correspondem ao estado verificado anteriormente.",
            )
            if not before.get("complete"):
                raise RuntimeError("Árvore UIA incompleta; não é seguro enviar sem observação completa.")

            if require_confirmation and (
                not confirm or not confirm(
                    "Enviar pelo WhatsApp Desktop",
                    f"Contato: {contact}\n\nMensagem exata:\n{message}\n\nEnviar uma vez?",
                )
            ):
                raise RuntimeError("Envio não autorizado pela confirmação configurada; nenhuma mensagem enviada.")

            # Reobserve after confirmation. The user may have changed chat/draft.
            before = self.wait(
                contact,
                message,
                lambda s: identity(s.get("conversation")) == identity(contact) and s.get("draft") == message,
                "A conversa ou o rascunho mudou durante a confirmação.",
            )
            if not before.get("complete"):
                raise RuntimeError("Árvore UIA incompleta antes do envio.")

            self.cancelled()
            self.send_attempted = True
            self.act("send", contact, message)
            tool_ok = True
            after = self.wait(
                contact,
                message,
                lambda s: verify_message(before, s, contact, message),
                "Não encontrei uma nova mensagem de saída confirmada na conversa correta.",
            )
            verification = {
                "verified": True,
                "scope": "goal",
                "reason": "Nova mensagem de saída com estado de envio observada na conversa correta.",
                "conversation": contact,
            }
            self.emit({"phase": "verify", **verification})
            return {
                "ok": True,
                "status": "verified",
                "tool_execution": {"ok": True, "send_attempted": True},
                "goal_verification": verification,
                "contact": contact,
                "draft": "",
                "events": self.events,
            }
        except Exception as exc:
            reason = str(exc) or type(exc).__name__
            verification = {"verified": False, "scope": "goal", "reason": reason}
            self.emit({"phase": "verify", **verification})
            return {
                "ok": False,
                "status": "uncertain" if self.send_attempted else "failed",
                "tool_execution": {"ok": tool_ok, "send_attempted": self.send_attempted},
                "goal_verification": verification,
                "error": reason,
                "events": self.events,
            }
