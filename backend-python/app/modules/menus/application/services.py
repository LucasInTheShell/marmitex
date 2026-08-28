from datetime import date
from decimal import Decimal
from uuid import UUID

from app.modules.menus.domain.entities import Menu, MenuItem
from app.modules.menus.domain.exceptions import EmptyMenuError
from app.modules.menus.domain.repositories import MenuRepository


class MenuApplicationService:
    def __init__(self, repository: MenuRepository) -> None:
        self.repository = repository

    async def list_items(self) -> list[MenuItem]:
        return await self.repository.list_items()

    async def create_item(
        self,
        name: str,
        description: str | None,
        size_options: list[str],
        price: Decimal | None,
    ) -> MenuItem:
        return await self.repository.create_item(
            name, description, size_options, price
        )

    async def list_week(self, start: date, end: date) -> list[Menu]:
        return await self.repository.between(start, end)

    async def save_week(self, menus: list[tuple[date, list[UUID]]]) -> None:
        await self.repository.save_week(menus)

    async def publish(self, dates: list[date]) -> None:
        if await self.repository.publish(dates) == 0:
            raise EmptyMenuError()

