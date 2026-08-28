from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class AccountRole(StrEnum):
    COMPANY = "company"
    KITCHEN = "kitchen"
    ADMIN = "admin"


@dataclass(frozen=True, slots=True)
class Account:
    id: UUID
    name: str
    email: str
    company_id: UUID | None
    role: AccountRole
    password_hash: str | None = None

