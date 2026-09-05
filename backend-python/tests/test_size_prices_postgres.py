from datetime import date
from decimal import Decimal
from uuid import uuid4

import psycopg
import pytest
from psycopg.rows import dict_row

from app.modules.menus.infrastructure.repository import PostgresMenuRepository
from tests.test_payments_postgres import event_loop_policy as event_loop_policy
from tests.test_payments_postgres import payment_database as payment_database


@pytest.mark.asyncio
async def test_size_prices_roundtrip_catalog_and_published_menu(payment_database):
    async with await psycopg.AsyncConnection.connect(
        payment_database, row_factory=dict_row
    ) as connection:
        repository = PostgresMenuRepository(connection)
        item = await repository.create_item(
            uuid4(),
            "Teste tamanhos",
            None,
            ["P", "G"],
            None,
            [],
            {"P": Decimal("12.99"), "G": Decimal("23.90")},
        )
        assert (await repository.item_by_id(item.id)).size_prices == item.size_prices
        assert (await repository.list_items())[0].price_for_size("G") == Decimal("23.90")
        day = date(2030, 1, 1)
        await repository.save_week([(day, [item.id])])
        await repository.publish([day])
        published = await repository.published_between(day, day)
        assert published[0].items[0].size_prices == item.size_prices
        await repository.update_item(item.id, item.name, None, ["P", "G"], Decimal("19"), [])
        saved = await repository.item_by_id(item.id)
        assert saved.size_prices == {}
        assert saved.price_for_size("G") == Decimal("19")
        # Reject invalid values even for writes bypassing the application.
        with pytest.raises(psycopg.errors.CheckViolation):
            async with connection.transaction():
                await connection.execute(
                    "update menu_items set size_prices = %s::jsonb where id = %s",
                    ('{"P":"-10"}', item.id),
                )
