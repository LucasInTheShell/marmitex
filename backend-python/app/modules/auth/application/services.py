from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.modules.auth.application.dto import LoginResult
from app.modules.auth.domain.entities import Account, AccountRole
from app.modules.auth.domain.exceptions import (
    AccountConflictError,
    DuplicateAccountEmailError,
    UnauthorizedError,
)
from app.modules.auth.domain.repositories import (
    AccountManagementRepository,
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


class AccountManagementService:
    def __init__(
        self,
        repository: AccountManagementRepository,
        passwords: PasswordService,
    ) -> None:
        self.repository = repository
        self.passwords = passwords

    async def list(self) -> list[Account]:
        return await self.repository.list_accounts()

    async def create(
        self,
        name: str,
        email: str,
        password: str,
        role: AccountRole,
        company_id: UUID | None,
    ) -> Account:
        if role is AccountRole.COMPANY and company_id is None:
            raise ValueError("Company accounts require a company")
        if role is not AccountRole.COMPANY and company_id is not None:
            raise ValueError("Only company accounts may reference a company")

        try:
            return await self.repository.create_account(
                name.strip(),
                email.lower(),
                self.passwords.hash(password),
                role,
                company_id,
            )
        except DuplicateAccountEmailError as error:
            raise AccountConflictError from error
