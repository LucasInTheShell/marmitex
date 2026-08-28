from uuid import uuid4

import pytest

from app.modules.auth.api.schemas import AccountCreate
from app.modules.auth.application.services import AccountManagementService
from app.modules.auth.domain.entities import Account, AccountRole
from app.modules.auth.domain.exceptions import (
    AccountConflictError,
    DuplicateAccountEmailError,
)


class FakeAccountRepository:
    def __init__(self) -> None:
        self.accounts: list[Account] = []
        self.created_with = None
        self.duplicate = False

    async def list_accounts(self) -> list[Account]:
        return self.accounts

    async def create_account(
        self, name, email, password_hash, role, company_id
    ) -> Account:
        if self.duplicate:
            raise DuplicateAccountEmailError
        self.created_with = (name, email, password_hash, role, company_id)
        account = Account(
            id=uuid4(),
            name=name,
            email=email,
            company_id=company_id,
            role=role,
        )
        self.accounts.append(account)
        return account


class FakePasswords:
    def hash(self, password: str) -> str:
        return f"hashed-{password}"

    def verify(self, password_hash: str, password: str) -> bool:
        return False


@pytest.mark.asyncio
async def test_admin_can_create_a_kitchen_account_with_hashed_password() -> None:
    repository = FakeAccountRepository()
    service = AccountManagementService(repository, FakePasswords())

    account = await service.create(
        "  Cozinha Mavi  ",
        "COZINHA@MAVI.LOCAL",
        "safe-password",
        AccountRole.KITCHEN,
        None,
    )

    assert account.role is AccountRole.KITCHEN
    assert repository.created_with == (
        "Cozinha Mavi",
        "cozinha@mavi.local",
        "hashed-safe-password",
        AccountRole.KITCHEN,
        None,
    )


@pytest.mark.asyncio
async def test_duplicate_account_email_becomes_an_application_conflict() -> None:
    repository = FakeAccountRepository()
    repository.duplicate = True
    service = AccountManagementService(repository, FakePasswords())

    with pytest.raises(AccountConflictError):
        await service.create(
            "Admin",
            "admin@mavi.local",
            "safe-password",
            AccountRole.ADMIN,
            None,
        )


def test_company_account_requires_company_id() -> None:
    with pytest.raises(ValueError):
        AccountCreate(
            name="Empresa",
            email="empresa@mavi.local",
            password="safe-password",
            role=AccountRole.COMPANY,
        )


def test_non_company_account_rejects_company_id() -> None:
    with pytest.raises(ValueError):
        AccountCreate(
            name="Admin",
            email="admin@mavi.local",
            password="safe-password",
            role=AccountRole.ADMIN,
            company_id=uuid4(),
        )
