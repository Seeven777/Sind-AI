class MemoryService:
    def __init__(self,repository): self.repository=repository
    def remember(self,content,**kwargs): return self.repository.add(content,**kwargs)
    def context(self,query=None,limit=6):
        if query:
            hits=self.repository.search(query,limit=limit)
            if hits: return hits
        return self.repository.recent(limit=limit)
class MemoryCurator:
    def review(self): return {'status':'not_enabled','reason':'curation arrives in a later milestone'}
