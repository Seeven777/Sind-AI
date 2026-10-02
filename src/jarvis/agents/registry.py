class AgentRegistry:
    def __init__(self): self._cards={}; self._runtimes={}
    def register_card(self,card): self._cards[card.agent_id]=card
    def register_runtime(self,agent_id,runtime):
        if agent_id not in self._cards: raise KeyError(f'Agent card missing: {agent_id}')
        self._runtimes[agent_id]=runtime
    def card(self,agent_id): return self._cards[agent_id]
    def runtime(self,agent_id): return self._runtimes[agent_id]
    def cards(self): return tuple(self._cards.values())
    def available(self): return tuple(c for c in self._cards.values() if c.agent_id in self._runtimes)
