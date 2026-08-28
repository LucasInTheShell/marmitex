from dataclasses import dataclass
from datetime import datetime

from app.modules.auth.domain.entities import Account


@dataclass(frozen=True, slots=True)
class LoginResult:
    token: str
    expires_at: datetime
    account: Account

