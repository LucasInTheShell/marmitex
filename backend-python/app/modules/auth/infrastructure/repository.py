from datetime import datetime
from uuid import UUID

from psycopg import AsyncConnection
from psycopg.errors import ForeignKeyViolation, UniqueViolation

from app.modules.auth.domain.entities import Account, AccountRole
from app.modules.auth.domain.exceptions import (
    DuplicateAccountEmailError,
    InvalidAccountCompanyError,
)
from app.modules.auth.infrastructure.models import account_from_row


class PostgresAuthRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self.connection = connection

    async def account_by_email(self, email: str) -> Account | None:
        result = await self.connection.execute(
            """
            select a.id, a.name, a.email, a.company_id, a.role, a.password_hash
            from accounts a
            left join companies c on c.id = a.company_id
            where lower(a.email) = lower(%s)
              and (a.company_id is null or c.active)
            """,
            (email,),
        )
        row = await result.fetchone()
        return account_from_row(row) if row else None

    async def account_by_session_hash(self, token_hash: str) -> Account | None:
        result = await self.connection.execute(
            """
            select a.id, a.name, a.email, a.company_id, a.role
            from sessions s
            join accounts a on a.id = s.account_id
            left join companies c on c.id = a.company_id
            where s.token_hash = %s
              and s.revoked_at is null
              and s.expires_at > now()
              and (a.company_id is null or c.active)
            """,
            (token_hash,),
        )
        row = await result.fetchone()
        return account_from_row(row) if row else None

    async def create_session(
        self, account_id: UUID, token_hash: str, expires_at: datetime
    ) -> None:
        await self.connection.execute(
            "insert into sessions (account_id, token_hash, expires_at) values (%s, %s, %s)",
            (account_id, token_hash, expires_at),
        )

    async def revoke_session(self, token_hash: str) -> None:
        await self.connection.execute(
            "update sessions set revoked_at = now() where token_hash = %s and revoked_at is null",
            (token_hash,),
        )

    async def list_accounts(self) -> list[Account]:
        result = await self.connection.execute(
            """
            select id, name, email, company_id, role
            from accounts
            order by role, name, email
            """
        )
        return [account_from_row(row) for row in await result.fetchall()]

    async def create_account(
        self,
        name: str,
        email: str,
        password_hash: str,
        role: AccountRole,
        company_id: UUID | None,
    ) -> Account:
        if company_id is not None:
            company_result = await self.connection.execute(
                "select id from companies where id = %s and active",
                (company_id,),
            )
            if not await company_result.fetchone():
                raise InvalidAccountCompanyError()

        try:
            result = await self.connection.execute(
                """
                insert into accounts (name, email, password_hash, company_id, role)
                values (%s, %s, %s, %s, %s)
                returning id, name, email, company_id, role
                """,
                (name, email, password_hash, company_id, role.value),
            )
            row = await result.fetchone()
        except UniqueViolation as error:
            raise DuplicateAccountEmailError from error
        except ForeignKeyViolation as error:
            raise InvalidAccountCompanyError from error

        return account_from_row(row)
