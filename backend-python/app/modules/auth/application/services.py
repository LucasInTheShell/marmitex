from datetime import UTC, datetime, timedelta

from app.modules.auth.application.dto import LoginResult
from app.modules.auth.domain.entities import Account
from app.modules.auth.domain.exceptions import UnauthorizedError
from app.modules.auth.domain.repositories import (
    AuthRepository,
    PasswordService,
    SessionService,
)


class AuthApplicationService:
    def __init__(
        self,
        repository: AuthRepository,
        passwords: PasswordService,
        sessions: SessionService,
        session_ttl_hours: int,
    ) -> None:
        self.repository = repository
        self.passwords = passwords
        self.sessions = sessions
        self.session_ttl_hours = session_ttl_hours

    async def login(self, email: str, password: str) -> LoginResult:
        account = await self.repository.account_by_email(email)
        if not account or not account.password_hash:
            raise UnauthorizedError()
        if not self.passwords.verify(account.password_hash, password):
            raise UnauthorizedError()

        token = self.sessions.create()
        expires_at = datetime.now(UTC) + timedelta(hours=self.session_ttl_hours)
        await self.repository.create_session(
            account.id, self.sessions.hash(token), expires_at
        )
        return LoginResult(token=token, expires_at=expires_at, account=account)

    async def authenticate(self, token: str) -> Account:
        account = await self.repository.account_by_session_hash(
            self.sessions.hash(token)
        )
        if not account:
            raise UnauthorizedError("Sessão inválida ou expirada.")
        return account

    async def logout(self, token: str) -> None:
        await self.repository.revoke_session(self.sessions.hash(token))

