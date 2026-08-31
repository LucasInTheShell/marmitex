from fastapi import APIRouter

from app.modules.auth.api.dependencies import AdminAccount, CurrentAccount
from app.modules.operations.api.dependencies import (
    OperationalSettingsServiceDependency,
)
from app.modules.operations.api.schemas import (
    OperationalSettingsResponse,
    OperationalSettingsUpdate,
)

router = APIRouter(prefix="/operational-settings", tags=["operational-settings"])


@router.get("", response_model=OperationalSettingsResponse)
async def get_operational_settings(
    _: CurrentAccount,
    service: OperationalSettingsServiceDependency,
):
    return await service.get()


@router.put("", response_model=OperationalSettingsResponse)
async def update_operational_settings(
    payload: OperationalSettingsUpdate,
    _: AdminAccount,
    service: OperationalSettingsServiceDependency,
):
    return await service.update_cutoff_lead(payload.order_cutoff_lead_minutes)
