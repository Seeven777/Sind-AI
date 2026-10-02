from dataclasses import dataclass, field
@dataclass(slots=True)
class Workspace:
    workspace_id: str
    name: str
    description: str = ''
    metadata: dict = field(default_factory=dict)
