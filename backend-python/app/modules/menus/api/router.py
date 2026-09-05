from datetime import date, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, File, Form, Query, Request, UploadFile, status
from pydantic import Json

from app.modules.auth.api.dependencies import AdminAccount, CompanyAccount
from app.modules.menus.api.dependencies import MenuServiceDependency
from app.modules.menus.api.schemas import (
    AvailableMenuResponse,
    MenuItemResponse,
    MenuResponse,
    SizeOption,
    WeekMenuUpdate,
    WeekPublishRequest,
)
from app.modules.menus.application.ports import (
    MAX_IMAGE_UPLOAD_BYTES,
    MAX_MENU_ITEM_IMAGES,
    ImageSource,
)
from app.modules.menus.domain.exceptions import InvalidMenuItemImageError

router = APIRouter(tags=["menus"])


@router.get("/menu-items", response_model=list[MenuItemResponse])
async def list_menu_items(_: AdminAccount, service: MenuServiceDependency):
    return await service.list_items()


@router.post("/menu-items", response_model=MenuItemResponse, status_code=status.HTTP_201_CREATED)
async def create_menu_item(
    _: AdminAccount,
    service: MenuServiceDependency,
    name: Annotated[str, Form(min_length=1, max_length=160)],
    size_options: Annotated[list[SizeOption], Form(min_length=1)],
    description: Annotated[str | None, Form(max_length=500)] = None,
    price: Annotated[
        Decimal | None,
        Form(ge=0, max_digits=10, decimal_places=2),
    ] = None,
    size_prices: Annotated[Json[dict[SizeOption, Decimal]] | None, Form()] = None,
    images: Annotated[list[UploadFile] | None, File()] = None,
    primary_image_index: Annotated[int, Form(ge=0)] = 0,
    image: Annotated[UploadFile | None, File()] = None,
):
    image_sources = await _image_sources(images, image)
    return await service.create_item(
        name.strip(),
        _optional_text(description),
        size_options,
        price,
        image_sources,
        primary_image_index,
        size_prices=size_prices,
    )


@router.put("/menu-items/{item_id}", response_model=MenuItemResponse)
async def update_menu_item(
    item_id: UUID,
    _: AdminAccount,
    service: MenuServiceDependency,
    name: Annotated[str, Form(min_length=1, max_length=160)],
    size_options: Annotated[list[SizeOption], Form(min_length=1)],
    description: Annotated[str | None, Form(max_length=500)] = None,
    price: Annotated[
        Decimal | None,
        Form(ge=0, max_digits=10, decimal_places=2),
    ] = None,
    size_prices: Annotated[Json[dict[SizeOption, Decimal]] | None, Form()] = None,
    images: Annotated[list[UploadFile] | None, File()] = None,
    remove_image_ids: Annotated[list[UUID] | None, Form()] = None,
    primary_image_id: Annotated[UUID | None, Form()] = None,
    primary_new_image_index: Annotated[int | None, Form(ge=0)] = None,
    image: Annotated[UploadFile | None, File()] = None,
    remove_image: Annotated[bool, Form()] = False,
):
    image_sources = await _image_sources(images, image)
    return await service.update_item(
        item_id,
        name.strip(),
        _optional_text(description),
        size_options,
        price,
        image_sources,
        remove_image_ids or [],
        primary_image_id,
        primary_new_image_index,
        remove_image,
        size_prices=size_prices,
    )


@router.delete("/menu-items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_menu_item(
    item_id: UUID,
    _: AdminAccount,
    service: MenuServiceDependency,
) -> None:
    await service.delete_item(item_id)


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
    await service.save_week([(menu.date, menu.menu_item_ids) for menu in payload.menus])


@router.post("/menus/week/publish", status_code=status.HTTP_204_NO_CONTENT)
async def publish_week(
    payload: WeekPublishRequest,
    _: AdminAccount,
    service: MenuServiceDependency,
) -> None:
    await service.publish(payload.dates)


async def _image_source(upload: UploadFile | None) -> ImageSource | None:
    if upload is None or not upload.filename:
        return None
    filename = upload.filename
    content_type = upload.content_type
    try:
        content = await upload.read(MAX_IMAGE_UPLOAD_BYTES + 1)
    finally:
        await upload.close()
    if len(content) > MAX_IMAGE_UPLOAD_BYTES:
        raise InvalidMenuItemImageError("A imagem deve ter no máximo 5 MB.")
    return ImageSource(
        content=content,
        content_type=content_type,
        filename=filename,
    )


async def _image_sources(
    uploads: list[UploadFile] | None,
    legacy_upload: UploadFile | None,
) -> list[ImageSource]:
    selected = list(uploads or [])
    if legacy_upload is not None and legacy_upload.filename:
        selected.append(legacy_upload)
    if len(selected) > MAX_MENU_ITEM_IMAGES:
        for upload in selected:
            await upload.close()
        raise InvalidMenuItemImageError(
            f"Um prato pode ter no máximo {MAX_MENU_ITEM_IMAGES} imagens."
        )
    sources: list[ImageSource] = []
    for upload in selected:
        source = await _image_source(upload)
        if source is not None:
            sources.append(source)
    return sources


def _optional_text(value: str | None) -> str | None:
    normalized = value.strip() if value else ""
    return normalized or None
