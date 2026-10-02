from dataclasses import dataclass, field
from typing import Protocol, Sequence
class ModelError(RuntimeError): pass
class ModelUnavailableError(ModelError): pass
@dataclass(slots=True,frozen=True)
class ChatMessage: role:str; content:str
@dataclass(slots=True)
class ModelResponse: content:str; model:str; provider:str; metadata:dict=field(default_factory=dict)
class ModelProvider(Protocol):
    provider_id:str
    def health(self)->dict: ...
    def list_models(self)->list[str]: ...
    def chat(self,messages:Sequence[ChatMessage],*,model:str|None=None,system:str|None=None)->ModelResponse: ...
