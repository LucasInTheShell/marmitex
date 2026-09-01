from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.modules.auth.domain.repositories import SessionService
from app.modules.employees.domain.entities import Employee, EmployeeDraft
from app.modules.employees.domain.exceptions import (
    EmployeeAccessDeniedError,
    EmployeeNotFoundError,
    InvalidEmployeeError,
)
from app.modules.employees.domain.repositories import EmployeeRepository
from app.modules.orders.domain.rules import normalized_cpf, normalized_phone


class EmployeeAccessService:
    def __init__(
        self,
        repository: EmployeeRepository,
        sessions: SessionService,
        session_ttl_hours: int,
    ) -> None:
        self.repository = repository
        self.sessions = sessions
        self.session_ttl_hours = session_ttl_hours

    async def login(self, cpf: str) -> tuple[str, datetime, Employee]:
        normalized = normalized_cpf(cpf)
        if len(normalized) != 11:
            raise EmployeeAccessDeniedError()
        employee = await self.repository.by_cpf(normalized)
        if employee is None:
            raise EmployeeAccessDeniedError()
        token = self.sessions.create()
        expires_at = datetime.now(UTC) + timedelta(hours=self.session_ttl_hours)
        await self.repository.create_session(
            employee.id, self.sessions.hash(token), expires_at
        )
        return token, expires_at, employee

    async def authenticate(self, token: str) -> Employee:
        employee = await self.repository.by_session_hash(self.sessions.hash(token))
        if employee is None:
            raise EmployeeAccessDeniedError()
        return employee

    async def logout(self, token: str) -> None:
        await self.repository.revoke_session(self.sessions.hash(token))


class EmployeeManagementService:
    def __init__(self, repository: EmployeeRepository) -> None:
        self.repository = repository

    async def list(self, company_id: UUID | None = None) -> list[Employee]:
        return await self.repository.list(company_id)

    async def by_id(self, employee_id: UUID) -> Employee:
        employee = await self.repository.by_id(employee_id)
        if employee is None:
            raise EmployeeNotFoundError()
        return employee

    async def create(
        self,
        company_id: UUID,
        name: str,
        cpf: str,
        phone: str,
        department: str,
        internal_id: str | None,
    ) -> Employee:
        normalized_name = name.strip()
        normalized_department = department.strip()
        normalized_document = normalized_cpf(cpf)
        normalized_contact = normalized_phone(phone)
        normalized_internal_id = internal_id.strip() or None if internal_id else None
        if not normalized_name or not normalized_department:
            raise InvalidEmployeeError("Nome e setor são obrigatórios.")
        if len(normalized_document) != 11:
            raise InvalidEmployeeError("Informe um CPF com 11 dígitos.")
        if not 10 <= len(normalized_contact) <= 15:
            raise InvalidEmployeeError("Informe um telefone válido.")
        return await self.repository.create(
            EmployeeDraft(
                company_id=company_id,
                name=normalized_name,
                cpf=normalized_document,
                phone=normalized_contact,
                department=normalized_department,
                internal_id=normalized_internal_id,
            )
        )

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
    ) -> Employee:
        normalized_name = name.strip() if name is not None else None
        normalized_department = department.strip() if department is not None else None
        normalized_phone_value = normalized_phone(phone) if phone is not None else None
        normalized_internal_id = (
            internal_id.strip() or None if internal_id is not None else None
        )
        if normalized_name == "" or normalized_department == "":
            raise InvalidEmployeeError("Nome e setor não podem ficar vazios.")
        if normalized_phone_value is not None and not 10 <= len(normalized_phone_value) <= 15:
            raise InvalidEmployeeError("Informe um telefone válido.")
        employee = await self.repository.update(
            employee_id,
            company_id,
            normalized_name,
            normalized_phone_value,
            normalized_department,
            normalized_internal_id,
            internal_id_was_set,
            active,
        )
        if employee is None:
            raise EmployeeNotFoundError()
        return employee
