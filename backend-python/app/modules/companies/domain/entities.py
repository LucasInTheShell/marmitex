from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Company:
    id: UUID
    name: str
    active: bool
    created_at: datetime
    access_email: str

