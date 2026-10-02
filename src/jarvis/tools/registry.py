class ToolRegistry:
    def __init__(self): self._tools={}
    def register(self,tool): self._tools[tool.tool_id]=tool
    def get(self,tool_id): return self._tools[tool_id]
    def list_ids(self): return tuple(sorted(self._tools))
