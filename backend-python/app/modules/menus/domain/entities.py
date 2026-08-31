from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class MenuItem:
    id: UUID
    name: str
    description: str | None
    size_options: list[str]
    price: Decimal | None


@dataclass(frozen=True, slots=True)
class Menu:
    id: UUID
    date: date
    menu_item_ids: list[UUID]
    published: bool


@dataclass(frozen=True, slots=True)
class AvailableMealSchedule:
    id: UUID
    label: str
    meal_time: time
    scheduled_for: datetime
    cutoff_at: datetime


@dataclass(frozen=True, slots=True)
class AvailableMenu:
    date: date
    items: list[MenuItem]
    available_schedules: list[AvailableMealSchedule]

