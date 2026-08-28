from datetime import date
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from app.modules.menus.domain.entities import Menu, MenuItem


class MenuRepository(Protocol):
    async def list_items(self) -> list[MenuItem]: ...

    async def create_item(
        self,
        name: str,
        description: str | None,
        size_options: list[str],
        price: Decimal | None,
    ) -> MenuItem: ...

    async def between(self, start: date, end: date) -> list[Menu]: ...

    async def save_week(self, menus: list[tuple[date, list[UUID]]]) -> None: ...

    async def publish(self, dates: list[date]) -> int: ...

