from datetime import date, datetime
from typing import Protocol
from uuid import UUID

from app.modules.orders.domain.entities import Order, OrderDraft, ProductionStatus


class DuplicateOrderRecordError(Exception):
    pass


class DuplicateOrderIdempotencyError(Exception):
    pass


class OrderRepository(Protocol):
    async def by_id(self, order_id: UUID, *, for_update: bool = False) -> Order | None: ...

    async def by_idempotency_key(self, company_id: UUID, idempotency_key: str) -> Order | None: ...

    async def create(self, draft: OrderDraft) -> Order: ...

    async def list(
        self,
        start: date,
        end: date,
        company_id: UUID | None = None,
        production_status: ProductionStatus | None = None,
        employee_cpf: str | None = None,
        *,
        active_only: bool = False,
    ) -> list[Order]: ...

    async def cancel(
        self,
        order_id: UUID,
        company_id: UUID,
        account_id: UUID,
        reason: str | None,
        cancelled_at: datetime,
    ) -> bool: ...

    async def update_status(
        self,
        order_id: UUID,
        expected_status: ProductionStatus,
        new_status: ProductionStatus,
        changed_at: datetime,
    ) -> bool: ...
