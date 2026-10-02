from __future__ import annotations


class CapabilityResolver:
    def __init__(self,*,agents=None,tools=None,skills=None,connectors=None):
        self.agents=agents
        self.tools=tools
        self.skills=skills
        self.connectors=connectors

    def resolve(self,capability):
        matches=[]
        if self.agents:
            for card in self.agents.cards():
                if capability in card.capabilities:
                    matches.append({
                        'kind':'agent','id':card.agent_id,
                        'active':card in self.agents.available(),
                    })
        if self.tools:
            for tool_id in self.tools.list_ids():
                if capability==tool_id or capability in tool_id:
                    matches.append({'kind':'tool','id':tool_id,'active':True})
        if self.skills:
            for skill_id in self.skills.capabilities().get(capability,[]):
                matches.append({'kind':'skill','id':skill_id,'active':True})
        if self.connectors:
            for connector in self.connectors.registry.all():
                if capability in {
                    connector.connector_id,
                    connector.connector_kind,
                    f'connector:{connector.connector_kind}',
                }:
                    health=connector.health()
                    matches.append({
                        'kind':'connector','id':connector.connector_id,
                        'active':health.get('status')=='healthy',
                        'health':health,
                    })
        return {
            'capability':capability,
            'status':'available' if any(x.get('active') for x in matches) else ('known' if matches else 'missing'),
            'matches':matches,
            'next':'use_existing' if any(x.get('active') for x in matches) else 'build_or_connect',
        }

    def inventory(self):
        result={'agents':[],'tools':[],'skills':[],'connectors':[]}
        if self.agents:
            result['agents']=[
                {
                    'id':c.agent_id,'name':c.name,'department':c.department,
                    'capabilities':list(c.capabilities),
                    'active':c in self.agents.available(),
                }
                for c in self.agents.cards()
            ]
        if self.tools:
            result['tools']=list(self.tools.list_ids())
        if self.skills:
            result['skills']=[
                {
                    'id':x['manifest'].skill_id,
                    'version':x['manifest'].version,
                    'state':x['state'],
                    'capabilities':list(x['manifest'].capabilities),
                }
                for x in self.skills.all()
            ]
        if self.connectors:
            result['connectors']=[
                {
                    'id':c.connector_id,
                    'kind':c.connector_kind,
                    'health':c.health(),
                }
                for c in self.connectors.registry.all()
            ]
        return result
