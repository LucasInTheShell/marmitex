from datetime import date
from decimal import Decimal
from uuid import UUID

from psycopg import AsyncConnection

from app.modules.menus.domain.entities import AvailableMenu, Menu, MenuItem, MenuItemImage
from app.modules.menus.infrastructure.models import menu_from_row, menu_item_from_row


class PostgresMenuRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self.connection = connection

    async def list_items(self) -> list[MenuItem]:
        result = await self.connection.execute(
            """
            select
                mi.id,
                mi.name,
                mi.description,
                mi.size_options,
                mi.price,
                coalesce((
                    select jsonb_agg(
                        jsonb_build_object(
                            'id', image.id,
                            'object_key', image.object_key,
                            'sort_order', image.sort_order,
                            'is_primary', image.is_primary
                        ) order by image.sort_order
                    )
                    from menu_item_images image
                    where image.menu_item_id = mi.id
                ), '[]'::jsonb) as images
            from menu_items mi
            where mi.deleted_at is null
            order by name
            """
        )
        return [menu_item_from_row(row) for row in await result.fetchall()]

    async def item_by_id(self, item_id: UUID) -> MenuItem | None:
        result = await self.connection.execute(
            """
            select
                mi.id,
                mi.name,
                mi.description,
                mi.size_options,
                mi.price,
                coalesce((
                    select jsonb_agg(
                        jsonb_build_object(
                            'id', image.id,
                            'object_key', image.object_key,
                            'sort_order', image.sort_order,
                            'is_primary', image.is_primary
                        ) order by image.sort_order
                    )
                    from menu_item_images image
                    where image.menu_item_id = mi.id
                ), '[]'::jsonb) as images
            from menu_items mi
            where mi.id = %s and mi.deleted_at is null
            """,
            (item_id,),
        )
        row = await result.fetchone()
        return menu_item_from_row(row) if row else None

    async def create_item(
        self,
        item_id: UUID,
        name: str,
        description: str | None,
        size_options: list[str],
        price: Decimal | None,
        images: list[MenuItemImage],
    ) -> MenuItem:
        async with self.connection.transaction():
            await self.connection.execute(
                """
                insert into menu_items (id, name, description, size_options, price)
                values (%s, %s, %s, %s, %s)
                """,
                (item_id, name, description, size_options, price),
            )
            await self._insert_images(item_id, images)
        return MenuItem(item_id, name, description, size_options, price, images)

    async def update_item(
        self,
        item_id: UUID,
        name: str,
        description: str | None,
        size_options: list[str],
        price: Decimal | None,
        images: list[MenuItemImage],
    ) -> MenuItem | None:
        async with self.connection.transaction():
            result = await self.connection.execute(
                """
                update menu_items
                set name = %s,
                    description = %s,
                    size_options = %s,
                    price = %s
                where id = %s and deleted_at is null
                """,
                (name, description, size_options, price, item_id),
            )
            if result.rowcount == 0:
                return None
            await self.connection.execute(
                "delete from menu_item_images where menu_item_id = %s",
                (item_id,),
            )
            await self._insert_images(item_id, images)
        return MenuItem(item_id, name, description, size_options, price, images)

    async def delete_item(self, item_id: UUID) -> MenuItem | None:
        current = await self.item_by_id(item_id)
        if current is None:
            return None
        async with self.connection.transaction():
            result = await self.connection.execute(
                """
                update menu_items
                set deleted_at = now()
                where id = %s and deleted_at is null
                """,
                (item_id,),
            )
            if result.rowcount == 0:
                return None
            await self.connection.execute(
                """
                update menus
                set menu_item_ids = array_remove(menu_item_ids, %s),
                    published = case
                        when cardinality(array_remove(menu_item_ids, %s)) = 0 then false
                        else published
                    end
                where %s = any(menu_item_ids)
                """,
                (item_id, item_id, item_id),
            )
        return current

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

    async def published_between(self, start: date, end: date) -> list[AvailableMenu]:
        result = await self.connection.execute(
            """
            select
                m.date,
                mi.id,
                mi.name,
                mi.description,
                mi.size_options,
                mi.price,
                coalesce((
                    select jsonb_agg(
                        jsonb_build_object(
                            'id', image.id,
                            'object_key', image.object_key,
                            'sort_order', image.sort_order,
                            'is_primary', image.is_primary
                        ) order by image.sort_order
                    )
                    from menu_item_images image
                    where image.menu_item_id = mi.id
                ), '[]'::jsonb) as images
            from menus m
            cross join lateral unnest(m.menu_item_ids)
                with ordinality as selected(item_id, position)
            join menu_items mi on mi.id = selected.item_id
            where m.published = true
              and mi.deleted_at is null
              and m.date between %s and %s
            order by m.date, selected.position
            """,
            (start, end),
        )
        menus: list[AvailableMenu] = []
        for row in await result.fetchall():
            if not menus or menus[-1].date != row["date"]:
                menus.append(AvailableMenu(date=row["date"], items=[], available_schedules=[]))
            menus[-1].items.append(menu_item_from_row(row))
        return menus

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

    async def _insert_images(
        self, item_id: UUID, images: list[MenuItemImage]
    ) -> None:
        for image in images:
            await self.connection.execute(
                """
                insert into menu_item_images (
                    id, menu_item_id, object_key, sort_order, is_primary
                ) values (%s, %s, %s, %s, %s)
                """,
                (
                    image.id,
                    item_id,
                    image.object_key,
                    image.sort_order,
                    image.is_primary,
                ),
            )
