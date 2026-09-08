from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.modules.orders.domain.entities import Order, ProductionStatus
from app.modules.orders.domain.exceptions import (
    OrderCannotBeCancelledError,
    OrderNotFoundError,
)
from app.modules.orders.domain.repositories import OrderRepository


class PendingPaymentCanceller(Protocol):
    async def cancel_pending_for_order(self, order_id: UUID, now: datetime) -> None: ...


class CancelOrder:
    def __init__(
        self,
        repository: OrderRepository,
        payment_canceller: PendingPaymentCanceller | None = None,
    ) -> None:
        self.repository = repository
        self.payment_canceller = payment_canceller

    async def execute(
        self,
        order_id: UUID,
        company_id: UUID,
        account_id: UUID,
        now: datetime,
        reason: str | None = None,
    ) -> Order:
        order = await self.repository.by_id(order_id, for_update=True)
        if order is None or order.company_id != company_id:
            raise OrderNotFoundError()
        if (
            order.production_status is not ProductionStatus.PENDING
            or order.cutoff_at is None
            or now >= order.cutoff_at
        ):
            raise OrderCannotBeCancelledError()

        if self.payment_canceller is not None:
            await self.payment_canceller.cancel_pending_for_order(order_id, now)

        cancelled = await self.repository.cancel(
            order_id,
            company_id,
            account_id,
            reason.strip() if reason else None,
            now,
        )
        if not cancelled:
            raise OrderCannotBeCancelledError()
        updated = await self.repository.by_id(order_id)
        if updated is None:
            raise OrderNotFoundError()
        return updated
