from dataclasses import dataclass, field
from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class MenuItemImage:
    id: UUID
    object_key: str
    sort_order: int
    is_primary: bool


@dataclass(frozen=True, slots=True)
class MenuItem:
    id: UUID
    name: str
    description: str | None
    size_options: list[str]
    price: Decimal | None
    images: list[MenuItemImage] = field(default_factory=list)
    size_prices: dict[str, Decimal] = field(default_factory=dict)

    def price_for_size(self, size: str) -> Decimal | None:
        if size not in self.size_options:
            return None
        return self.size_prices.get(size, self.price)


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
