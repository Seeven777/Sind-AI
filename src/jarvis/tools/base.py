from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol
class RiskLevel(StrEnum): READ='read'; PREPARE='prepare'; INTERNAL_WRITE='internal_write'; EXTERNAL_WRITE='external_write'; DESTRUCTIVE='destructive'; FINANCIAL='financial'; CREDENTIAL='credential'
@dataclass(slots=True)
class ToolResult: success:bool; output:dict=field(default_factory=dict); evidence:dict=field(default_factory=dict); error:str|None=None
class Tool(Protocol):
    tool_id:str; risk:RiskLevel
    def execute(self,payload:dict)->ToolResult: ...
    def verify(self,payload:dict,result:ToolResult)->ToolResult: ...
