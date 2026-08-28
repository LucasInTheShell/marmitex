from psycopg import AsyncConnection
from psycopg.errors import UniqueViolation

from app.modules.companies.domain.entities import Company
from app.modules.companies.domain.exceptions import DuplicateCompanyEmailError
from app.modules.companies.infrastructure.models import company_from_row


class PostgresCompanyRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self.connection = connection

    async def list(self) -> list[Company]:
        result = await self.connection.execute(
            """
            select c.id, c.name, c.active, c.created_at, a.email as access_email
            from companies c
            join accounts a on a.company_id = c.id and a.role = 'company'
            order by c.name
            """
        )
        return [company_from_row(row) for row in await result.fetchall()]

    async def create(self, name: str, email: str, password_hash: str) -> Company:
        try:
            async with self.connection.transaction():
                result = await self.connection.execute(
                    """
                    insert into companies (name) values (%s)
                    returning id, name, active, created_at
                    """,
                    (name,),
                )
                company = await result.fetchone()
                await self.connection.execute(
                    """
                    insert into accounts (name, email, password_hash, company_id, role)
                    values (%s, %s, %s, %s, 'company')
                    """,
                    (name, email, password_hash, company["id"]),
                )
        except UniqueViolation as error:
            raise DuplicateCompanyEmailError from error
        return company_from_row(company, email)

