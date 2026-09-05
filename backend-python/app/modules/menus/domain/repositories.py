from datetime import date
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from app.modules.menus.domain.entities import AvailableMenu, Menu, MenuItem, MenuItemImage


class MenuRepository(Protocol):
    async def list_items(self) -> list[MenuItem]: ...

    async def item_by_id(self, item_id: UUID) -> MenuItem | None: ...

    async def create_item(
        self,
        item_id: UUID,
        name: str,
        description: str | None,
        size_options: list[str],
        price: Decimal | None,
        images: list[MenuItemImage],
        size_prices: dict[str, Decimal] | None = None,
    ) -> MenuItem: ...

    async def update_item(
        self,
        item_id: UUID,
        name: str,
        description: str | None,
        size_options: list[str],
        price: Decimal | None,
        images: list[MenuItemImage],
        size_prices: dict[str, Decimal] | None = None,
    ) -> MenuItem | None: ...

    async def delete_item(self, item_id: UUID) -> MenuItem | None: ...

    async def between(self, start: date, end: date) -> list[Menu]: ...

    async def published_between(self, start: date, end: date) -> list[AvailableMenu]: ...

    async def save_week(self, menus: list[tuple[date, list[UUID]]]) -> None: ...

    async def publish(self, dates: list[date]) -> int: ...
