from dataclasses import dataclass,field
@dataclass(slots=True)
class IPCMessage: message_type:str; request_id:str; payload:dict=field(default_factory=dict)
PROTOCOL_VERSION=1
