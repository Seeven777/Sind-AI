from __future__ import annotations

from .base import RiskLevel,ToolResult


class WhatsAppSendMessageTool:
    tool_id='whatsapp.send_message'
    risk=RiskLevel.EXTERNAL_WRITE

    def __init__(self,service):
        self.service=service

    def execute(self,payload):
        try:
            result=self.service.send_message(
                str(payload['contact']),
                str(payload['message']),
                int(payload.get('timeout',20)),
            )
            return ToolResult(
                bool(result.get('success')),result,
                {
                    'sent_invoked':bool(result.get('sent_invoked')),
                    'verified_in_ui':bool(result.get('verified')),
                    'observed_text':result.get('observed_text'),
                },
                None if result.get('success') else 'Mensagem não pôde ser verificada no WhatsApp.'
            )
        except Exception as exc:
            return ToolResult(False,error=str(exc))

    def verify(self,payload,result):
        ok=bool(
            result.success and result.evidence.get('sent_invoked')
            and result.evidence.get('verified_in_ui')
        )
        return ToolResult(
            ok,result.output,result.evidence,
            None if ok else (result.error or 'Envio não verificado.')
        )
