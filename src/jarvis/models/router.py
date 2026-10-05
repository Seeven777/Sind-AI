from dataclasses import dataclass


@dataclass(slots=True,frozen=True)
class ModelRoute:
    provider:str
    model:str
    reason:str


class ModelRouter:
    def __init__(self,default_provider,default_model,registry=None,*,premium_provider=None,privacy_mode='hybrid'):
        self.default_provider=default_provider
        self.default_model=default_model
        self.registry=registry
        self.premium_provider=premium_provider
        self.privacy_mode=privacy_mode

    def _healthy_external(self,*,capability,budget):
        if self.registry is None:
            return None
        for provider in self.registry.providers():
            pid=provider.provider_id
            if pid==self.default_provider:
                continue
            if self.premium_provider and budget=='premium' and pid!=self.premium_provider:
                continue
            meta=self.registry.metadata(pid)
            if budget=='free' and meta.get('paid',True):
                continue
            health=provider.health()
            if health.get('status')!='healthy':
                continue
            capabilities=set(meta.get('capabilities') or ['chat'])
            if capability not in capabilities and 'general' not in capabilities:
                continue
            return provider
        return None

    def route(self,*,capability='chat',privacy='local',budget='free'):
        # Explicit local privacy always wins. No cloud provider can leak into a
        # local-only request, even when a premium provider is configured.
        if privacy=='local' or self.registry is None:
            return ModelRoute(
                self.default_provider,self.default_model,
                f'local default for {capability}; privacy={privacy}; budget={budget}'
            )

        provider=self._healthy_external(capability=capability,budget=budget)
        if provider is not None:
            return ModelRoute(
                provider.provider_id,getattr(provider,'default_model',''),
                f'external route for {capability}; privacy={privacy}; budget={budget}'
            )
        return ModelRoute(
            self.default_provider,self.default_model,
            f'fallback local for {capability}; privacy={privacy}; budget={budget}'
        )
