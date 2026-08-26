from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.modules.auth.domain.entities import Account


class AuthRepository(Protocol):
    async def account_by_email(self, email: str) -> Account | None: ...

    async def account_by_session_hash(self, token_hash: str) -> Account | None: ...

    async def create_session(
        self, account_id: UUID, token_hash: str, expires_at: datetime
    ) -> None: ...

    async def revoke_session(self, token_hash: str) -> None: ...


class PasswordService(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password_hash: str, password: str) -> bool: ...


class SessionService(Protocol):
    def create(self) -> str: ...

    def hash(self, token: str) -> str: ...

