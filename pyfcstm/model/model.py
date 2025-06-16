from dataclasses import dataclass
from typing import Optional


@dataclass
class Transition:
    name: str
    event: Optional[str]
    pass


class State:
    pass
