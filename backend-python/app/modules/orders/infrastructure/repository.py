from uuid import UUID

from psycopg import AsyncConnection

from app.modules.orders.domain.entities import Order
from app.modules.orders.infrastructure.models import order_from_row


class PostgresOrderRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self.connection = connection

    async def by_id(self, order_id: UUID) -> Order | None:
        result = await self.connection.execute(
            "select * from orders where id = %s", (order_id,)
        )
        row = await result.fetchone()
        return order_from_row(row) if row else None

