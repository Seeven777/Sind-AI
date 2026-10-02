from jarvis.tools import WhatsAppSendMessageTool


class FakeWhatsApp:
    def send_message(self,contact,message,timeout=20):
        return {
            "success":True,"contact":contact,"message":message,
            "sent_invoked":True,"verified":True,"observed_text":message,
            "window":"WhatsApp",
        }


def test_whatsapp_tool_requires_verified_ui_result():
    tool=WhatsAppSendMessageTool(FakeWhatsApp())
    result=tool.execute({"contact":"Teste","message":"Olá"})
    assert result.success
    verified=tool.verify({},result)
    assert verified.success
    assert verified.evidence["verified_in_ui"] is True
