from fastapi import APIRouter, status

from app.modules.auth.api.dependencies import (
    AccountManagementServiceDependency,
    AdminAccount,
)
from app.modules.auth.api.schemas import AccountCreate, AccountResponse

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("", response_model=list[AccountResponse])
async def list_accounts(
    _: AdminAccount,
    service: AccountManagementServiceDependency,
):
    return await service.list()


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    payload: AccountCreate,
    _: AdminAccount,
    service: AccountManagementServiceDependency,
):
    return await service.create(
        payload.name,
        str(payload.email),
        payload.password,
        payload.role,
        payload.company_id,
    )
