from datetime import date, datetime
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Header, Query, Request, status

from app.core.security import bearer_token
from app.modules.auth.api.dependencies import Credentials, CurrentAccount
from app.modules.auth.domain.entities import AccountRole
from app.modules.auth.domain.exceptions import ForbiddenError
from app.modules.employees.api.dependencies import (
    CurrentEmployee,
    EmployeeAccessServiceDependency,
    EmployeeManagementServiceDependency,
)
from app.modules.employees.api.schemas import (
    EmployeeAccessRequest,
    EmployeeAccessResponse,
    EmployeeCreateRequest,
    EmployeeOrderCreateRequest,
    EmployeePublicResponse,
    EmployeeResponse,
    EmployeeUpdateRequest,
)
from app.modules.employees.domain.exceptions import InvalidEmployeeError
from app.modules.menus.api.dependencies import MenuServiceDependency
from app.modules.menus.api.schemas import AvailableMenuResponse
from app.modules.orders.api.dependencies import CreateOrderDependency
from app.modules.orders.api.schemas import OrderResponse
from app.modules.orders.application.create_order import CreateOrderCommand, RequestedOrderItem

router = APIRouter(tags=["employees"])


@router.post("/employee/access", response_model=EmployeeAccessResponse)
async def employee_access(
    payload: EmployeeAccessRequest, service: EmployeeAccessServiceDependency
):
    token, expires_at, employee = await service.login(payload.cpf)
    return EmployeeAccessResponse(
        token=token, expires_at=expires_at, employee=employee
    )


@router.get("/employee/me", response_model=EmployeePublicResponse)
async def employee_me(employee: CurrentEmployee):
    return employee


@router.post("/employee/logout", status_code=status.HTTP_204_NO_CONTENT)
async def employee_logout(
    credentials: Credentials,
    service: EmployeeAccessServiceDependency,
) -> None:
    token = bearer_token(credentials)
    if token:
        await service.logout(token)


@router.get("/employee/menus/available", response_model=list[AvailableMenuResponse])
async def employee_available_menus(
    request: Request,
    employee: CurrentEmployee,
    service: MenuServiceDependency,
    start: Annotated[date, Query()],
    end: Annotated[date, Query()],
):
    time_zone = request.app.state.settings.app_time_zone
    return await service.available(
        employee.company_id,
        start,
        end,
        datetime.now(ZoneInfo(time_zone)),
        time_zone,
    )


@router.post(
    "/employee/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED
)
async def create_employee_order(
    request: Request,
    payload: EmployeeOrderCreateRequest,
    employee: CurrentEmployee,
    use_case: CreateOrderDependency,
    idempotency_key: Annotated[
        str | None, Header(alias="Idempotency-Key", min_length=1, max_length=120)
    ] = None,
):
    time_zone = request.app.state.settings.app_time_zone
    return await use_case.execute(
        CreateOrderCommand(
            company_id=employee.company_id,
            date=payload.date,
            meal_schedule_id=payload.meal_schedule_id,
            employee_name=employee.name,
            employee_phone=employee.phone,
            employee_department=employee.department,
            employee_cpf=employee.cpf,
            employee_internal_id=employee.internal_id,
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
        datetime.now(ZoneInfo(time_zone)),
        time_zone,
    )


@router.get("/employees", response_model=list[EmployeeResponse])
async def list_employees(
    account: CurrentAccount,
    service: EmployeeManagementServiceDependency,
    company_id: Annotated[UUID | None, Query()] = None,
):
    if account.role is AccountRole.COMPANY:
        assert account.company_id is not None
        if company_id is not None and company_id != account.company_id:
            raise ForbiddenError()
        company_id = account.company_id
    elif account.role is not AccountRole.ADMIN:
        raise ForbiddenError()
    return await service.list(company_id)


@router.post("/employees", response_model=EmployeeResponse, status_code=201)
async def create_employee(
    payload: EmployeeCreateRequest,
    account: CurrentAccount,
    service: EmployeeManagementServiceDependency,
):
    if account.role is AccountRole.COMPANY:
        assert account.company_id is not None
        if payload.company_id is not None and payload.company_id != account.company_id:
            raise ForbiddenError()
        company_id = account.company_id
    elif account.role is AccountRole.ADMIN:
        if payload.company_id is None:
            raise InvalidEmployeeError("A empresa é obrigatória para o administrador.")
        company_id = payload.company_id
    else:
        raise ForbiddenError()
    return await service.create(
        company_id,
        payload.name,
        payload.cpf,
        payload.phone,
        payload.department,
        payload.internal_id,
    )


@router.patch("/employees/{employee_id}", response_model=EmployeeResponse)
async def update_employee(
    employee_id: UUID,
    payload: EmployeeUpdateRequest,
    account: CurrentAccount,
    service: EmployeeManagementServiceDependency,
):
    existing = await service.by_id(employee_id)
    if account.role is AccountRole.COMPANY:
        assert account.company_id is not None
        if existing.company_id != account.company_id:
            raise ForbiddenError()
    elif account.role is not AccountRole.ADMIN:
        raise ForbiddenError()
    return await service.update(
        employee_id,
        existing.company_id,
        payload.name,
        payload.phone,
        payload.department,
        payload.internal_id,
        "internal_id" in payload.model_fields_set,
        payload.active,
    )
