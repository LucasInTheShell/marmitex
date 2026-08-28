from typing import Protocol
from uuid import UUID

from app.modules.orders.domain.entities import Order


class OrderRepository(Protocol):
    async def by_id(self, order_id: UUID) -> Order | None: ...

