from dataclasses import dataclass, field


@dataclass
class Task:
    type: str = ""
    payload: dict = field(default_factory=dict)
    retries: int = 0
