from dataclasses import dataclass, field
from typing import Protocol
@dataclass(slots=True,frozen=True)
class AgentCard:
    agent_id:str; name:str; department:str; mission:str; capabilities:tuple[str,...]=(); tools:tuple[str,...]=(); model_capability:str='chat'; active:bool=False
@dataclass(slots=True)
class AgentResult:
    success:bool; summary:str; artifact_id:str|None=None; artifact_path:str|None=None; metadata:dict=field(default_factory=dict)
class Agent(Protocol):
    card:AgentCard
    async def run(self,objective:str,*,task_id:str)->AgentResult: ...
