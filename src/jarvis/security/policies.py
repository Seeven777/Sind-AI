class PolicyDecision:
    ALLOW='allow'
    APPROVAL='approval'
    BLOCK='block'


class PolicyEngine:
    """Safe defaults without depending on the tools package."""

    def decide(self,risk):
        value=getattr(risk,'value',str(risk))
        if value in {'read','prepare'}:
            return PolicyDecision.ALLOW
        if value in {'internal_write','external_write','destructive'}:
            return PolicyDecision.APPROVAL
        return PolicyDecision.BLOCK
