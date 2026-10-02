from __future__ import annotations

from .base import RiskLevel,ToolResult


class MCPToolAdapter:
    """Safest default: every external MCP action requires approval."""

    risk=RiskLevel.EXTERNAL_WRITE

    def __init__(self,server_id,tool_name,client):
        self.server_id=server_id
        self.tool_name=tool_name
        self.client=client
        self.tool_id=f'mcp.{server_id}.{tool_name}'

    def execute(self,payload):
        try:
            result=self.client.call_tool(self.tool_name,payload)
            return ToolResult(
                True,{'result':result},
                {'mcp_server':self.server_id,'mcp_tool':self.tool_name,'rpc_completed':True}
            )
        except Exception as exc:
            return ToolResult(False,error=str(exc))

    def verify(self,payload,result):
        ok=bool(result.success and result.evidence.get('rpc_completed'))
        return ToolResult(ok,result.output,result.evidence,result.error if not ok else None)
