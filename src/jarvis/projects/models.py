from dataclasses import dataclass, field
@dataclass(slots=True)
class Project:
    project_id: str
    name: str
    objective: str
    status: str = 'planned'
    metadata: dict = field(default_factory=dict)
