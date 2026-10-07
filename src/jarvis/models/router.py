from dataclasses import dataclass


@dataclass(slots=True,frozen=True)
class ModelRoute:
    provider:str
    model:str
    reason:str


class ModelRouter:
    def __init__(
        self,default_provider,default_model,registry=None,*,premium_provider=None,
        privacy_mode='hybrid',local_models=None
    ):
        self.default_provider=default_provider
        self.default_model=default_model
        self.registry=registry
        self.premium_provider=premium_provider
        self.privacy_mode=privacy_mode
        self.local_models={str(k):str(v) for k,v in (local_models or {}).items() if v}

    def local_model(self,capability='chat'):
        return (
            self.local_models.get(capability)
            or self.local_models.get('general')
            or self.default_model
        )

    def model_profile(self):
        keys=('chat','fast','reasoning','creative','coding','tool_use','general')
        return {key:self.local_model(key) for key in keys}

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
        local_model=self.local_model(capability)
        # Explicit local privacy always wins. No cloud provider can leak into a
        # local-only request, even when a premium provider is configured.
        if privacy=='local' or self.registry is None:
            return ModelRoute(
                self.default_provider,local_model,
                f'local role model for {capability}; privacy={privacy}; budget={budget}'
            )

        provider=self._healthy_external(capability=capability,budget=budget)
        if provider is not None:
            return ModelRoute(
                provider.provider_id,getattr(provider,'default_model',''),
                f'external route for {capability}; privacy={privacy}; budget={budget}'
            )
        return ModelRoute(
            self.default_provider,local_model,
            f'fallback local role model for {capability}; privacy={privacy}; budget={budget}'
        )
