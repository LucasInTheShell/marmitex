from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials

from app.api.dependencies import DatabaseConnection
from app.core.security import bearer, bearer_token
from app.modules.auth.application.services import (
    AccountManagementService,
    AuthApplicationService,
)
from app.modules.auth.domain.entities import Account, AccountRole
from app.modules.auth.domain.exceptions import ForbiddenError, UnauthorizedError
from app.modules.auth.infrastructure.password import ArgonPasswordService
from app.modules.auth.infrastructure.repository import PostgresAuthRepository
from app.modules.auth.infrastructure.session import OpaqueSessionService

Credentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]


def auth_service(
    request: Request, connection: DatabaseConnection
) -> AuthApplicationService:
    return AuthApplicationService(
        PostgresAuthRepository(connection),
        ArgonPasswordService(),
        OpaqueSessionService(),
        request.app.state.settings.session_ttl_hours,
    )


AuthServiceDependency = Annotated[AuthApplicationService, Depends(auth_service)]


def account_management_service(
    connection: DatabaseConnection,
) -> AccountManagementService:
    return AccountManagementService(
        PostgresAuthRepository(connection),
        ArgonPasswordService(),
    )


AccountManagementServiceDependency = Annotated[
    AccountManagementService, Depends(account_management_service)
]


async def current_account(
    credentials: Credentials, service: AuthServiceDependency
) -> Account:
    token = bearer_token(credentials)
    if not token:
        raise UnauthorizedError("Sessão inválida ou expirada.")
    return await service.authenticate(token)


CurrentAccount = Annotated[Account, Depends(current_account)]


async def admin_account(account: CurrentAccount) -> Account:
    if account.role is not AccountRole.ADMIN:
        raise ForbiddenError()
    return account


async def kitchen_account(account: CurrentAccount) -> Account:
    if account.role is not AccountRole.KITCHEN:
        raise ForbiddenError()
    return account


async def company_account(account: CurrentAccount) -> Account:
    if account.role is not AccountRole.COMPANY:
        raise ForbiddenError()
    return account


AdminAccount = Annotated[Account, Depends(admin_account)]
KitchenAccount = Annotated[Account, Depends(kitchen_account)]
CompanyAccount = Annotated[Account, Depends(company_account)]
