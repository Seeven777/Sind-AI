from dataclasses import dataclass, field
@dataclass(slots=True)
class Briefing:
    title: str = 'Bom dia'
    items: list[dict] = field(default_factory=list)
    generated_at: str | None = None
