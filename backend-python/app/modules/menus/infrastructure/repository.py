from datetime import date
from decimal import Decimal
from uuid import UUID

from psycopg import AsyncConnection

from app.modules.menus.domain.entities import Menu, MenuItem
from app.modules.menus.infrastructure.models import menu_from_row, menu_item_from_row


class PostgresMenuRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self.connection = connection

    async def list_items(self) -> list[MenuItem]:
        result = await self.connection.execute(
            "select id, name, description, size_options, price from menu_items order by name"
        )
        return [menu_item_from_row(row) for row in await result.fetchall()]

    async def create_item(
        self,
        name: str,
        description: str | None,
        size_options: list[str],
        price: Decimal | None,
    ) -> MenuItem:
        result = await self.connection.execute(
            """
            insert into menu_items (name, description, size_options, price)
            values (%s, %s, %s, %s)
            returning id, name, description, size_options, price
            """,
            (name, description, size_options, price),
        )
        return menu_item_from_row(await result.fetchone())

    async def between(self, start: date, end: date) -> list[Menu]:
        result = await self.connection.execute(
            """
            select id, date, menu_item_ids, published
            from menus
            where date between %s and %s
            order by date
            """,
            (start, end),
        )
        return [menu_from_row(row) for row in await result.fetchall()]

    async def save_week(self, menus: list[tuple[date, list[UUID]]]) -> None:
        async with self.connection.transaction():
            for menu_date, menu_item_ids in menus:
                await self.connection.execute(
                    """
                    insert into menus (date, menu_item_ids, published)
                    values (%s, %s, false)
                    on conflict (date) do update
                    set menu_item_ids = excluded.menu_item_ids,
                        published = case
                            when menus.menu_item_ids = excluded.menu_item_ids then menus.published
                            else false
                        end
                    """,
                    (menu_date, menu_item_ids),
                )

    async def publish(self, dates: list[date]) -> int:
        result = await self.connection.execute(
            """
            update menus set published = true
            where date = any(%s) and cardinality(menu_item_ids) > 0
            """,
            (dates,),
        )
        return result.rowcount

