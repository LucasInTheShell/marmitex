from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from psycopg import AsyncConnection
from psycopg.errors import UniqueViolation

from app.modules.orders.domain.entities import Order, OrderDraft, ProductionStatus
from app.modules.orders.domain.repositories import (
    DuplicateOrderIdempotencyError,
    DuplicateOrderRecordError,
)
from app.modules.orders.infrastructure.models import (
    order_from_row,
    order_item_from_row,
)

ORDER_HEADER_SELECT = """
    select
        o.id,
        o.order_number,
        o.company_id,
        c.name as company_name,
        o.date,
        o.meal_schedule_id,
        o.meal_schedule_label,
        o.scheduled_for,
        o.cutoff_at,
        o.employee_name,
        o.employee_phone,
        o.employee_department,
        o.employee_cpf,
        o.employee_internal_id,
        o.production_status,
        o.payment_method,
        o.payment_status,
        o.total_price,
        o.idempotency_key,
        o.request_fingerprint,
        o.created_at,
        o.updated_at,
        o.cancelled_at,
        o.cancellation_reason
    from orders o
    join companies c on c.id = o.company_id
"""


class PostgresOrderRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self.connection = connection

    async def by_id(self, order_id: UUID, *, for_update: bool = False) -> Order | None:
        result = await self.connection.execute(
            f"{ORDER_HEADER_SELECT} where o.id = %s" + (" for update of o" if for_update else ""),
            (order_id,),
        )
        row = await result.fetchone()
        if row is None:
            return None
        return (await self._with_items([row]))[0]

    async def by_idempotency_key(self, company_id: UUID, idempotency_key: str) -> Order | None:
        result = await self.connection.execute(
            f"{ORDER_HEADER_SELECT} where o.company_id = %s and o.idempotency_key = %s",
            (company_id, idempotency_key),
        )
        row = await result.fetchone()
        if row is None:
            return None
        return (await self._with_items([row]))[0]

    async def create(self, draft: OrderDraft) -> Order:
        try:
            async with self.connection.transaction():
                result = await self.connection.execute(
                    """
                    insert into orders (
                        company_id,
                        date,
                        meal_schedule_id,
                        meal_schedule_label,
                        scheduled_for,
                        cutoff_at,
                        employee_name,
                        employee_phone,
                        employee_department,
                        employee_cpf,
                        employee_internal_id,
                        total_price,
                        idempotency_key,
                        request_fingerprint,
                        payment_method,
                        payment_status
                    )
                    values (
                        %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s,
                        %s, %s
                    )
                    returning id
                    """,
                    (
                        draft.company_id,
                        draft.date,
                        draft.meal_schedule_id,
                        draft.meal_schedule_label,
                        draft.scheduled_for,
                        draft.cutoff_at,
                        draft.employee_name,
                        draft.employee_phone,
                        draft.employee_department,
                        draft.employee_cpf,
                        draft.employee_internal_id,
                        draft.total_price,
                        draft.idempotency_key,
                        draft.request_fingerprint,
                        draft.payment_method.value,
                        draft.payment_status.value,
                    ),
                )
                order_id = (await result.fetchone())["id"]
                for position, item in enumerate(draft.items):
                    await self.connection.execute(
                        """
                        insert into order_items (
                            order_id,
                            position,
                            menu_item_id,
                            item_name,
                            item_description,
                            size,
                            quantity,
                            unit_price,
                            subtotal,
                            notes
                        )
                        values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            order_id,
                            position,
                            item.menu_item_id,
                            item.item_name,
                            item.item_description,
                            item.size,
                            item.quantity,
                            item.unit_price,
                            item.subtotal,
                            item.notes,
                        ),
                    )
        except UniqueViolation as error:
            if error.diag.constraint_name == "orders_company_idempotency_unique":
                raise DuplicateOrderIdempotencyError from error
            if error.diag.constraint_name == "one_order_per_company_person_day":
                raise DuplicateOrderRecordError from error
            raise

        order = await self.by_id(order_id)
        if order is None:
            raise RuntimeError("Created order could not be loaded")
        return order

    async def list(
        self,
        start: date,
        end: date,
        company_id: UUID | None = None,
        production_status: ProductionStatus | None = None,
        employee_cpf: str | None = None,
        *,
        active_only: bool = False,
    ) -> list[Order]:
        clauses = ["o.date between %s and %s"]
        parameters: list[object] = [start, end]
        if company_id is not None:
            clauses.append("o.company_id = %s")
            parameters.append(company_id)
        if production_status is not None:
            clauses.append("o.production_status = %s")
            parameters.append(production_status.value)
        if employee_cpf is not None:
            clauses.append("o.employee_cpf = %s")
            parameters.append(employee_cpf)
        if active_only:
            clauses.append("o.production_status in ('pending', 'printed', 'separated')")
        query = (
            ORDER_HEADER_SELECT
            + " where "
            + " and ".join(clauses)
            + " order by o.date, o.created_at, o.order_number"
        )
        result = await self.connection.execute(query, parameters)
        return await self._with_items(list(await result.fetchall()))

    async def cancel(
        self,
        order_id: UUID,
        company_id: UUID,
        account_id: UUID,
        reason: str | None,
        cancelled_at: datetime,
    ) -> bool:
        result = await self.connection.execute(
            """
            update orders
            set production_status = 'cancelled',
                cancelled_at = %s,
                cancelled_by_account_id = %s,
                cancellation_reason = %s,
                updated_at = %s
            where id = %s
              and company_id = %s
              and production_status = 'pending'
              and cutoff_at > %s
            """,
            (
                cancelled_at,
                account_id,
                reason,
                cancelled_at,
                order_id,
                company_id,
                cancelled_at,
            ),
        )
        return result.rowcount == 1

    async def update_status(
        self,
        order_id: UUID,
        expected_status: ProductionStatus,
        new_status: ProductionStatus,
        changed_at: datetime,
    ) -> bool:
        result = await self.connection.execute(
            """
            update orders
            set production_status = %s, updated_at = %s
            where id = %s and production_status = %s
            """,
            (new_status.value, changed_at, order_id, expected_status.value),
        )
        return result.rowcount == 1

    async def _with_items(self, rows: list[dict]) -> list[Order]:
        if not rows:
            return []
        order_ids = [row["id"] for row in rows]
        result = await self.connection.execute(
            """
            select
                id,
                order_id,
                menu_item_id,
                item_name,
                item_description,
                size,
                quantity,
                unit_price,
                subtotal,
                notes
            from order_items
            where order_id = any(%s)
            order by order_id, position
            """,
            (order_ids,),
        )
        items_by_order: dict[UUID, list] = {}
        for item_row in await result.fetchall():
            items_by_order.setdefault(item_row["order_id"], []).append(
                order_item_from_row(item_row)
            )
        return [order_from_row(row, items_by_order.get(row["id"], [])) for row in rows]
