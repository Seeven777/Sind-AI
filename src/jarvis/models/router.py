from dataclasses import dataclass


@dataclass(slots=True,frozen=True)
class ModelRoute:
    provider:str
    model:str
    reason:str


class ModelRouter:
    def __init__(self,default_provider,default_model,registry=None):
        self.default_provider=default_provider
        self.default_model=default_model
        self.registry=registry

    def route(self,*,capability='chat',privacy='local',budget='free'):
        if privacy=='local' or self.registry is None:
            return ModelRoute(
                self.default_provider,self.default_model,
                f'local default for {capability}; privacy={privacy}; budget={budget}'
            )

        for provider in self.registry.providers():
            pid=provider.provider_id
            if pid==self.default_provider:continue
            meta=self.registry.metadata(pid)
            if budget=='free' and meta.get('paid',True):
                continue
            health=provider.health()
            if health.get('status')!='healthy':
                continue
            capabilities=set(meta.get('capabilities') or ['chat'])
            if capability not in capabilities and 'general' not in capabilities:
                continue
            return ModelRoute(
                pid,getattr(provider,'default_model',''),
                f'external route for {capability}; privacy={privacy}; budget={budget}'
            )
        return ModelRoute(
            self.default_provider,self.default_model,
            f'fallback local for {capability}; privacy={privacy}; budget={budget}'
        )
