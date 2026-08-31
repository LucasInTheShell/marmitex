from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class OperationalSettings:
    order_cutoff_lead_minutes: int
    updated_at: datetime
