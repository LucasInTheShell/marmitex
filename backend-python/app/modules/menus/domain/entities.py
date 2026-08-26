from dataclasses import dataclass
from datetime import date
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

