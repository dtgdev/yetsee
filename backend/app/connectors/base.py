from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(slots=True)
class Observation:
    source: str
    title: str
    url: str
    text: str = ""
    published_at: datetime | None = None
    metadata: dict | None = None


class Connector(Protocol):
    name: str

    async def fetch(self) -> list[Observation]: ...
