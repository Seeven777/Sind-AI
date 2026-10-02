from jarvis.security import PolicyDecision,PolicyEngine
from jarvis.tools import RiskLevel,SystemTimeTool
def test_tool_and_policy():
 tool=SystemTimeTool(); r=tool.verify({},tool.execute({})); assert r.success; assert r.evidence['source']=='system_clock'; p=PolicyEngine(); assert p.decide(RiskLevel.READ)==PolicyDecision.ALLOW; assert p.decide(RiskLevel.EXTERNAL_WRITE)==PolicyDecision.APPROVAL; assert p.decide(RiskLevel.FINANCIAL)==PolicyDecision.BLOCK
