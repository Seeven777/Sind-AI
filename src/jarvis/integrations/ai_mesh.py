from __future__ import annotations

from dataclasses import dataclass

from .creative_studio import CreativeStudioClient
from .hermes import HermesAgentBridge
from .whatsapp_gateway import WhatsAppGatewayClient


@dataclass(slots=True)
class AIMesh:
    hermes: HermesAgentBridge
    whatsapp_gateway: WhatsAppGatewayClient
    creative: CreativeStudioClient

    def health(self) -> dict:
        return {
            "hermes": self.hermes.health(),
            "whatsapp_gateway": self.whatsapp_gateway.health(),
            "creative_studio": self.creative.health(),
        }
