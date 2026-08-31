from datetime import date, datetime
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Header, Query, Request, status

from app.modules.auth.api.dependencies import CompanyAccount, CurrentAccount, KitchenAccount
from app.modules.auth.domain.entities import AccountRole
from app.modules.auth.domain.exceptions import ForbiddenError
from app.modules.orders.api.dependencies import (
    CancelOrderDependency,
    CreateOrderDependency,
    OrderServiceDependency,
)
from app.modules.orders.api.schemas import (
    DailyProductionSummaryResponse,
    KitchenOrderResponse,
    OrderCancellationRequest,
    OrderCreateRequest,
    OrderResponse,
    ProductionStatusUpdateRequest,
)
from app.modules.orders.application.create_order import (
    CreateOrderCommand,
    RequestedOrderItem,
)
from app.modules.orders.domain.entities import ProductionStatus

router = APIRouter(tags=["orders"])


def local_now(request: Request) -> tuple[datetime, str]:
    time_zone = request.app.state.settings.app_time_zone
    return datetime.now(ZoneInfo(time_zone)), time_zone


@router.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    request: Request,
    payload: OrderCreateRequest,
    account: CompanyAccount,
    use_case: CreateOrderDependency,
    idempotency_key: Annotated[
        str | None,
        Header(alias="Idempotency-Key", min_length=1, max_length=120),
    ] = None,
):
    assert account.company_id is not None
    now, time_zone = local_now(request)
    return await use_case.execute(
        CreateOrderCommand(
            company_id=account.company_id,
            date=payload.date,
            meal_schedule_id=payload.meal_schedule_id,
            employee_name=payload.employee_name,
            employee_phone=payload.employee_phone,
            employee_department=payload.employee_department,
            employee_cpf=payload.employee_cpf,
            employee_internal_id=payload.employee_internal_id,
            items=[
                RequestedOrderItem(
                    menu_item_id=item.menu_item_id,
                    size=item.size,
                    quantity=item.quantity,
                    notes=item.notes,
                )
                for item in payload.items
            ],
            idempotency_key=idempotency_key,
        ),
        now,
        time_zone,
    )


@router.get("/orders", response_model=list[OrderResponse])
async def list_orders(
    request: Request,
    account: CurrentAccount,
    service: OrderServiceDependency,
    start: Annotated[date | None, Query()] = None,
    end: Annotated[date | None, Query()] = None,
    company_id: Annotated[UUID | None, Query()] = None,
    production_status: Annotated[ProductionStatus | None, Query(alias="status")] = None,
):
    today = datetime.now(ZoneInfo(request.app.state.settings.app_time_zone)).date()
    start = start or end or today
    end = end or start
    if account.role is AccountRole.COMPANY:
        assert account.company_id is not None
        if company_id is not None and company_id != account.company_id:
            raise ForbiddenError()
        company_id = account.company_id
    elif account.role is not AccountRole.ADMIN:
        raise ForbiddenError()
    return await service.list(start, end, company_id, production_status)


@router.get("/kitchen/production-board", response_model=list[KitchenOrderResponse])
async def production_board(
    board_date: Annotated[date, Query(alias="date")],
    _: KitchenAccount,
    service: OrderServiceDependency,
):
    return await service.production_board(board_date)


@router.get("/kitchen/production-summary", response_model=DailyProductionSummaryResponse)
async def production_summary(
    request: Request,
    summary_date: Annotated[date, Query(alias="date")],
    _: KitchenAccount,
    service: OrderServiceDependency,
):
    return await service.production_summary(
        summary_date, request.app.state.settings.app_time_zone
    )


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: UUID,
    account: CurrentAccount,
    service: OrderServiceDependency,
):
    if account.role is AccountRole.COMPANY:
        assert account.company_id is not None
        return await service.by_id(order_id, account.company_id)
    if account.role is AccountRole.ADMIN:
        return await service.by_id(order_id)
    raise ForbiddenError()


@router.post("/orders/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    request: Request,
    order_id: UUID,
    payload: OrderCancellationRequest,
    account: CompanyAccount,
    use_case: CancelOrderDependency,
):
    assert account.company_id is not None
    now, _ = local_now(request)
    return await use_case.execute(
        order_id,
        account.company_id,
        account.id,
        now,
        payload.reason,
    )


@router.patch("/orders/{order_id}/status", response_model=KitchenOrderResponse)
async def update_order_status(
    request: Request,
    order_id: UUID,
    payload: ProductionStatusUpdateRequest,
    account: CurrentAccount,
    service: OrderServiceDependency,
):
    if account.role not in {AccountRole.KITCHEN, AccountRole.ADMIN}:
        raise ForbiddenError()
    now, _ = local_now(request)
    return await service.update_production_status(
        order_id, ProductionStatus(payload.production_status), now
    )
