from datetime import date, datetime, time
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

SizeOption = Literal["P", "M", "G"]


class MenuItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=500)
    size_options: list[SizeOption] = Field(min_length=1)
    price: Decimal | None = Field(
        default=None, ge=0, max_digits=10, decimal_places=2
    )


class MenuItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    size_options: list[SizeOption]
    price: float | None


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

