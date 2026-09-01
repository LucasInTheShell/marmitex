from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.modules.employees.domain.entities import Employee, EmployeeDraft


class EmployeeRepository(Protocol):
    async def list(self, company_id: UUID | None = None) -> list[Employee]: ...

    async def by_id(self, employee_id: UUID) -> Employee | None: ...

    async def by_cpf(self, cpf: str) -> Employee | None: ...

    async def by_session_hash(self, token_hash: str) -> Employee | None: ...

    async def create(self, draft: EmployeeDraft) -> Employee: ...

    async def update(
        self,
        employee_id: UUID,
        company_id: UUID,
        name: str | None,
        phone: str | None,
        department: str | None,
        internal_id: str | None,
        internal_id_was_set: bool,
        active: bool | None,
    ) -> Employee | None: ...

    async def create_session(
        self, employee_id: UUID, token_hash: str, expires_at: datetime
    ) -> None: ...

    async def revoke_session(self, token_hash: str) -> None: ...
