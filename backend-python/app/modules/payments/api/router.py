from datetime import datetime
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Header, HTTPException, Request

from app.modules.auth.api.dependencies import CompanyAccount
from app.modules.employees.api.dependencies import CurrentEmployee
from app.modules.payments.api.dependencies import PaymentServiceDependency
from app.modules.payments.api.schemas import (
    PaymentMethodChangeResponse,
    PixCheckoutResponse,
)

router = APIRouter(tags=["payments"])


def local_now(request: Request) -> datetime:
    return datetime.now(ZoneInfo(request.app.state.settings.app_time_zone))


@router.post("/orders/{order_id}/payments/pix", response_model=PixCheckoutResponse)
async def company_pix_checkout(
    request: Request,
    order_id: UUID,
    account: CompanyAccount,
    service: PaymentServiceDependency,
):
    assert account.company_id is not None
    return await service.pix_checkout(order_id, account.company_id, local_now(request))


@router.post("/employee/orders/{order_id}/payments/pix", response_model=PixCheckoutResponse)
async def employee_pix_checkout(
    request: Request,
    order_id: UUID,
    employee: CurrentEmployee,
    service: PaymentServiceDependency,
):
    return await service.pix_checkout(
        order_id, employee.company_id, local_now(request), employee.cpf
    )


@router.post(
    "/orders/{order_id}/payment-method/delivery",
    response_model=PaymentMethodChangeResponse,
)
async def company_switch_to_delivery(
    request: Request,
    order_id: UUID,
    account: CompanyAccount,
    service: PaymentServiceDependency,
):
    assert account.company_id is not None
    order = await service.switch_to_delivery(order_id, account.company_id, local_now(request))
    return PaymentMethodChangeResponse(order=order)


@router.post(
    "/employee/orders/{order_id}/payment-method/delivery",
    response_model=PaymentMethodChangeResponse,
)
async def employee_switch_to_delivery(
    request: Request,
    order_id: UUID,
    employee: CurrentEmployee,
    service: PaymentServiceDependency,
):
    order = await service.switch_to_delivery(
        order_id, employee.company_id, local_now(request), employee.cpf
    )
    return PaymentMethodChangeResponse(order=order)


@router.post("/webhooks/asaas")
async def asaas_webhook(
    request: Request,
    service: PaymentServiceDependency,
    asaas_token: Annotated[str | None, Header(alias="asaas-access-token")] = None,
) -> dict[str, bool]:
    payload = await request.body()
    if len(payload) > 256_000:
        raise HTTPException(status_code=413)
    event = service.gateway.parse_webhook(payload, asaas_token)
    await service.payments.enqueue_event(event)
    return {"received": True}
