from datetime import date, datetime, time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

SizeOption = Literal["P", "M", "G"]


class MenuItemImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    url: str
    sort_order: int
    is_primary: bool


class MenuItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    size_options: list[SizeOption]
    price: float | None
    size_prices: dict[SizeOption, float] = Field(default_factory=dict)
    image_url: str | None = None
    images: list[MenuItemImageResponse] = Field(default_factory=list)


class MenuResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    date: date
    menu_item_ids: list[UUID]
    published: bool


class AvailableMealScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    label: str
    meal_time: time
    scheduled_for: datetime
    cutoff_at: datetime


class AvailableMenuResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date
    items: list[MenuItemResponse]
    available_schedules: list[AvailableMealScheduleResponse]


class MenuSelection(BaseModel):
    date: date
    menu_item_ids: list[UUID]


class WeekMenuUpdate(BaseModel):
    menus: list[MenuSelection] = Field(min_length=1, max_length=7)


class WeekPublishRequest(BaseModel):
    dates: list[date] = Field(min_length=1, max_length=7)
