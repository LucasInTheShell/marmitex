from uuid import uuid4

import pytest

from app.modules.auth.application.services import AuthApplicationService
from app.modules.auth.domain.entities import Account, AccountRole
from app.modules.auth.domain.exceptions import UnauthorizedError


class FakeAuthRepository:
    def __init__(self, account: Account | None) -> None:
        self.account = account
        self.created_session = None

    async def account_by_email(self, email: str):
        return self.account

    async def account_by_session_hash(self, token_hash: str):
        return self.account if token_hash == "hashed-session" else None

    async def create_session(self, account_id, token_hash, expires_at) -> None:
        self.created_session = (account_id, token_hash, expires_at)

    async def revoke_session(self, token_hash: str) -> None:
        return None


class FakePasswords:
    def hash(self, password: str) -> str:
        return f"hashed-{password}"

    def verify(self, password_hash: str, password: str) -> bool:
        return password_hash == f"hashed-{password}"


class FakeSessions:
    def create(self) -> str:
        return "session"

    def hash(self, token: str) -> str:
        return f"hashed-{token}"


def service_for(account: Account | None):
    repository = FakeAuthRepository(account)
    service = AuthApplicationService(
        repository, FakePasswords(), FakeSessions(), session_ttl_hours=24
    )
    return service, repository


@pytest.mark.asyncio
async def test_login_uses_ports_and_persists_only_the_token_hash() -> None:
    account = Account(
        id=uuid4(),
        name="Admin",
        email="admin@mavi.local",
        company_id=None,
        role=AccountRole.ADMIN,
        password_hash="hashed-secret",
    )
    service, repository = service_for(account)

    result = await service.login(account.email, "secret")

    assert result.token == "session"
    assert repository.created_session[1] == "hashed-session"
    assert repository.created_session[1] != "session"


@pytest.mark.asyncio
async def test_login_rejects_an_invalid_password() -> None:
    account = Account(
        id=uuid4(),
        name="Admin",
        email="admin@mavi.local",
        company_id=None,
        role=AccountRole.ADMIN,
        password_hash="hashed-secret",
    )
    service, _ = service_for(account)

    with pytest.raises(UnauthorizedError):
        await service.login(account.email, "wrong")
