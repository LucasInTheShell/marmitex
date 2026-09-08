from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Employee:
    id: UUID
    company_id: UUID
    company_name: str
    name: str
    cpf: str
    phone: str
    department: str
    internal_id: str | None
    active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class EmployeeDraft:
    company_id: UUID
    name: str
    cpf: str
    phone: str
    department: str
    internal_id: str | None
