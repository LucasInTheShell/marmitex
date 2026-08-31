from datetime import date, datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Query, Request, status

from app.modules.auth.api.dependencies import AdminAccount, CompanyAccount
from app.modules.menus.api.dependencies import MenuServiceDependency
from app.modules.menus.api.schemas import (
    AvailableMenuResponse,
    MenuItemCreate,
    MenuItemResponse,
    MenuResponse,
    WeekMenuUpdate,
    WeekPublishRequest,
)

router = APIRouter(tags=["menus"])


@router.get("/menu-items", response_model=list[MenuItemResponse])
async def list_menu_items(_: AdminAccount, service: MenuServiceDependency):
    return await service.list_items()


@router.post(
    "/menu-items", response_model=MenuItemResponse, status_code=status.HTTP_201_CREATED
)
async def create_menu_item(
    payload: MenuItemCreate, _: AdminAccount, service: MenuServiceDependency
):
    return await service.create_item(
        payload.name.strip(), payload.description, payload.size_options, payload.price
    )


@router.get("/menus", response_model=list[MenuResponse])
async def list_menus(
    _: AdminAccount,
    service: MenuServiceDependency,
    start: Annotated[date, Query()],
    end: Annotated[date, Query()],
):
    return await service.list_week(start, end)


@router.get("/menus/available", response_model=list[AvailableMenuResponse])
async def available_menus(
    request: Request,
    account: CompanyAccount,
    service: MenuServiceDependency,
    start: Annotated[date, Query()],
    end: Annotated[date, Query()],
):
    assert account.company_id is not None
    time_zone = request.app.state.settings.app_time_zone
    return await service.available(
        account.company_id,
        start,
        end,
        datetime.now(ZoneInfo(time_zone)),
        time_zone,
    )


@router.put("/menus/week", status_code=status.HTTP_204_NO_CONTENT)
async def save_week(
    payload: WeekMenuUpdate, _: AdminAccount, service: MenuServiceDependency
) -> None:
    await service.save_week(
        [(menu.date, menu.menu_item_ids) for menu in payload.menus]
    )


@router.post("/menus/week/publish", status_code=status.HTTP_204_NO_CONTENT)
async def publish_week(
    payload: WeekPublishRequest,
    _: AdminAccount,
    service: MenuServiceDependency,
) -> None:
    await service.publish(payload.dates)
