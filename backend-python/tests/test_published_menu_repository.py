from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app.modules.menus.infrastructure.repository import PostgresMenuRepository


class FakeResult:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows

    async def fetchall(self) -> list[dict]:
        return self.rows


class FakeConnection:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.query = ""
        self.params = ()

    async def execute(self, query: str, params: tuple):
        self.query = " ".join(query.lower().split())
        self.params = params
        return FakeResult(self.rows)


@pytest.mark.asyncio
async def test_available_query_excludes_unpublished_and_empty_menus() -> None:
    connection = FakeConnection([])
    repository = PostgresMenuRepository(connection)  # type: ignore[arg-type]

    menus = await repository.published_between(
        date(2026, 8, 31), date(2026, 9, 4)
    )

    assert menus == []
    assert "m.published = true" in connection.query
    # CROSS JOIN faz um array vazio produzir zero linhas, ocultando o cardápio vazio.
    assert "cross join lateral unnest(m.menu_item_ids)" in connection.query
    assert "with ordinality" in connection.query
    assert "mi.deleted_at is null" in connection.query
    assert connection.params == (date(2026, 8, 31), date(2026, 9, 4))


@pytest.mark.asyncio
async def test_available_query_uses_database_sizes_prices_and_item_order() -> None:
    first_id = uuid4()
    second_id = uuid4()
    connection = FakeConnection(
        [
            {
                "date": date(2026, 8, 31),
                "id": first_id,
                "name": "Executivo",
                "description": None,
                "size_options": ["M", "G"],
                "price": Decimal("23.50"),
            },
            {
                "date": date(2026, 8, 31),
                "id": second_id,
                "name": "Frango grelhado",
                "description": "Arroz, feijão e salada",
                "size_options": ["P", "M", "G"],
                "price": Decimal("24.90"),
            },
        ]
    )
    repository = PostgresMenuRepository(connection)  # type: ignore[arg-type]

    menus = await repository.published_between(
        date(2026, 8, 31), date(2026, 9, 4)
    )

    assert [item.id for item in menus[0].items] == [first_id, second_id]
    assert menus[0].items[0].size_options == ["M", "G"]
    assert menus[0].items[0].price == Decimal("23.50")
    assert "order by m.date, selected.position" in connection.query
