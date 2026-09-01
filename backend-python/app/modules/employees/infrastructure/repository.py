from datetime import datetime
from uuid import UUID

from psycopg import AsyncConnection
from psycopg.errors import ForeignKeyViolation, UniqueViolation

from app.modules.employees.domain.entities import Employee, EmployeeDraft
from app.modules.employees.domain.exceptions import (
    EmployeeCpfConflictError,
    InvalidEmployeeError,
)
from app.modules.employees.infrastructure.models import employee_from_row

_EMPLOYEE_COLUMNS = """
    e.id, e.company_id, c.name as company_name, e.name, e.cpf, e.phone,
    e.department, e.internal_id, e.active, e.created_at, e.updated_at
"""


class PostgresEmployeeRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self.connection = connection

    async def list(self, company_id: UUID | None = None) -> list[Employee]:
        result = await self.connection.execute(
            f"""
            select {_EMPLOYEE_COLUMNS}
            from employees e
            join companies c on c.id = e.company_id
            where (%s::uuid is null or e.company_id = %s)
            order by c.name, e.name, e.cpf
            """,
            (company_id, company_id),
        )
        return [employee_from_row(row) for row in await result.fetchall()]

    async def by_id(self, employee_id: UUID) -> Employee | None:
        result = await self.connection.execute(
            f"""
            select {_EMPLOYEE_COLUMNS}
            from employees e
            join companies c on c.id = e.company_id
            where e.id = %s
            """,
            (employee_id,),
        )
        row = await result.fetchone()
        return employee_from_row(row) if row else None

    async def by_cpf(self, cpf: str) -> Employee | None:
        result = await self.connection.execute(
            f"""
            select {_EMPLOYEE_COLUMNS}
            from employees e
            join companies c on c.id = e.company_id
            where e.cpf = %s and e.active and c.active
            """,
            (cpf,),
        )
        row = await result.fetchone()
        return employee_from_row(row) if row else None

    async def by_session_hash(self, token_hash: str) -> Employee | None:
        result = await self.connection.execute(
            f"""
            select {_EMPLOYEE_COLUMNS}
            from employee_sessions s
            join employees e on e.id = s.employee_id
            join companies c on c.id = e.company_id
            where s.token_hash = %s
              and s.revoked_at is null
              and s.expires_at > now()
              and e.active
              and c.active
            """,
            (token_hash,),
        )
        row = await result.fetchone()
        return employee_from_row(row) if row else None

    async def create(self, draft: EmployeeDraft) -> Employee:
        try:
            result = await self.connection.execute(
                """
                insert into employees
                    (company_id, name, cpf, phone, department, internal_id)
                values (%s, %s, %s, %s, %s, %s)
                returning id
                """,
                (
                    draft.company_id,
                    draft.name,
                    draft.cpf,
                    draft.phone,
                    draft.department,
                    draft.internal_id,
                ),
            )
            row = await result.fetchone()
        except UniqueViolation as error:
            raise EmployeeCpfConflictError() from error
        except ForeignKeyViolation as error:
            raise InvalidEmployeeError("A empresa informada não existe.") from error
        employee = await self.by_id(row["id"])
        assert employee is not None
        return employee

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
    ) -> Employee | None:
        result = await self.connection.execute(
            """
            update employees
            set name = coalesce(%s, name),
                phone = coalesce(%s, phone),
                department = coalesce(%s, department),
                internal_id = case when %s then %s else internal_id end,
                active = coalesce(%s, active),
                updated_at = now()
            where id = %s and company_id = %s
            returning id
            """,
            (
                name,
                phone,
                department,
                internal_id_was_set,
                internal_id,
                active,
                employee_id,
                company_id,
            ),
        )
        row = await result.fetchone()
        return await self.by_id(row["id"]) if row else None

    async def create_session(
        self, employee_id: UUID, token_hash: str, expires_at: datetime
    ) -> None:
        await self.connection.execute(
            """
            insert into employee_sessions (employee_id, token_hash, expires_at)
            values (%s, %s, %s)
            """,
            (employee_id, token_hash, expires_at),
        )

    async def revoke_session(self, token_hash: str) -> None:
        await self.connection.execute(
            """
            update employee_sessions
            set revoked_at = now()
            where token_hash = %s and revoked_at is null
            """,
            (token_hash,),
        )
