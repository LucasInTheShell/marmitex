from fastapi import APIRouter, status

from app.core.security import bearer_token
from app.modules.auth.api.dependencies import (
    AuthServiceDependency,
    Credentials,
    CurrentAccount,
)
from app.modules.auth.api.schemas import AccountResponse, LoginRequest, LoginResponse
from app.modules.auth.domain.exceptions import UnauthorizedError

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, service: AuthServiceDependency):
    result = await service.login(str(payload.email), payload.password)
    return LoginResponse(
        token=result.token,
        expires_at=result.expires_at,
        account=AccountResponse.model_validate(result.account),
    )


@router.get("/me", response_model=AccountResponse)
async def me(account: CurrentAccount):
    return account


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(credentials: Credentials, service: AuthServiceDependency) -> None:
    token = bearer_token(credentials)
    if not token:
        raise UnauthorizedError("Sessão inválida ou expirada.")
    await service.logout(token)

