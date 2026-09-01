from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from app.modules.menus.domain.entities import AvailableMealSchedule


@dataclass(frozen=True, slots=True)
class MenuItemImageResult:
    id: UUID
    url: str
    sort_order: int
    is_primary: bool


@dataclass(frozen=True, slots=True)
class MenuItemResult:
    id: UUID
    name: str
    description: str | None
    size_options: list[str]
    price: Decimal | None
    image_url: str | None
    images: list[MenuItemImageResult]


@dataclass(frozen=True, slots=True)
class AvailableMenuResult:
    date: date
    items: list[MenuItemResult]
    available_schedules: list[AvailableMealSchedule]
