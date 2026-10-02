class ModelRegistry:
    def __init__(self):
        self._providers={}
        self._metadata={}

    def register(self,provider,metadata=None):
        self._providers[provider.provider_id]=provider
        self._metadata[provider.provider_id]=metadata or {}

    def get(self,provider_id):
        if provider_id not in self._providers:
            raise KeyError(f"Model provider not registered: {provider_id}")
        return self._providers[provider_id]

    def providers(self):
        return tuple(self._providers.values())

    def metadata(self,provider_id):
        return self._metadata.get(provider_id,{})

    def health(self):
        result={}
        for key,value in self._providers.items():
            try:health=value.health()
            except Exception as exc:health={'status':'error','error':str(exc)}
            health['metadata']=self._metadata.get(key,{})
            result[key]=health
        return result
