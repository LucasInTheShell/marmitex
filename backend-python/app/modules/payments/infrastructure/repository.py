from dataclasses import asdict
from datetime import datetime
from uuid import UUID

from psycopg import AsyncConnection
from psycopg.types.json import Jsonb

from app.modules.orders.domain.entities import PaymentStatus
from app.modules.payments.domain.entities import OrderPayment, PaymentEvent
from app.modules.payments.infrastructure.models import payment_from_row

PAYMENT_COLUMNS = """
    id, order_id, provider::text as provider, provider_payment_id, provider_status, amount_cents,
    currency, requested_expires_at, paid_at, failed_at, cancelled_at,
    created_at, updated_at, confirmed_at
"""


class PostgresPaymentRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self.connection = connection

    async def by_order_id(self, order_id: UUID) -> OrderPayment | None:
        result = await self.connection.execute(
            f"select {PAYMENT_COLUMNS} from order_payments where order_id = %s",
            (order_id,),
        )
        row = await result.fetchone()
        return payment_from_row(row) if row else None

    async def by_provider_payment_id(
        self, provider: str, provider_payment_id: str
    ) -> OrderPayment | None:
        result = await self.connection.execute(
            f"""
            select {PAYMENT_COLUMNS}
            from order_payments
            where provider = %s and provider_payment_id = %s
            """,
            (provider, provider_payment_id),
        )
        row = await result.fetchone()
        return payment_from_row(row) if row else None

    async def customer_id(self, provider: str, company_id: UUID, employee_cpf: str) -> str | None:
        # Serialize customer creation across different orders for the same employee.
        await self.connection.execute(
            "select pg_advisory_xact_lock(hashtextextended(%s, 0))",
            (f"payment-customer:{provider}:{company_id}:{employee_cpf}",),
        )
        result = await self.connection.execute(
            """
            select provider_customer_id
            from payment_customers
            where provider = %s and company_id = %s and employee_cpf = %s
            """,
            (provider, company_id, employee_cpf),
        )
        row = await result.fetchone()
        return row["provider_customer_id"] if row else None

    async def save_customer_id(
        self,
        provider: str,
        company_id: UUID,
        employee_cpf: str,
        provider_customer_id: str,
    ) -> str:
        await self.connection.execute(
            """
            insert into payment_customers (
                provider, company_id, employee_cpf, provider_customer_id
            ) values (%s, %s, %s, %s)
            on conflict (provider, company_id, employee_cpf) do nothing
            """,
            (provider, company_id, employee_cpf, provider_customer_id),
        )
        stored = await self.customer_id(provider, company_id, employee_cpf)
        if stored is None:
            raise RuntimeError("Payment customer could not be persisted")
        return stored

    async def create(
        self,
        order_id: UUID,
        provider: str,
        provider_payment_id: str,
        provider_status: str,
        amount_cents: int,
        currency: str,
        requested_expires_at: datetime,
    ) -> OrderPayment:
        await self.connection.execute(
            """
            insert into order_payments (
                order_id, provider, provider_payment_id, provider_status,
                amount_cents, currency, requested_expires_at
            ) values (%s, %s, %s, %s, %s, %s, %s)
            on conflict (order_id) do nothing
            """,
            (
                order_id,
                provider,
                provider_payment_id,
                provider_status,
                amount_cents,
                currency,
                requested_expires_at,
            ),
        )
        payment = await self.by_order_id(order_id)
        if payment is None:
            raise RuntimeError("Payment could not be persisted")
        return payment

    async def apply_event(
        self,
        event: PaymentEvent,
        payment_status: PaymentStatus,
    ) -> bool:
        async with self.connection.transaction():
            inserted = await self.connection.execute(
                """
                insert into payment_webhook_events (
                    provider, provider_event_id, event_type,
                    provider_payment_id, processed_at
                ) values (%s, %s, %s, %s, %s)
                on conflict (provider, provider_event_id) do nothing
                returning provider_event_id
                """,
                (
                    event.provider,
                    event.id,
                    event.type,
                    event.provider_payment_id,
                    event.occurred_at,
                ),
            )
            if await inserted.fetchone() is None:
                return False

            current = await self.connection.execute(
                """
                select p.order_id, p.paid_at, o.payment_status::text as payment_status
                from order_payments p join orders o on o.id = p.order_id
                where p.provider = %s and p.provider_payment_id = %s
                for update of p
                """,
                (event.provider, event.provider_payment_id),
            )
            row = await current.fetchone()
            if row is None:
                return True
            if row["payment_status"] in {"refunded", "review_required"} and (
                payment_status is not PaymentStatus.REFUNDED
            ):
                return True
            if row["paid_at"] is not None and payment_status in {
                PaymentStatus.PENDING,
                PaymentStatus.PROCESSING,
                PaymentStatus.EXPIRED,
                PaymentStatus.CANCELLED,
                PaymentStatus.FAILED,
            }:
                return True

            paid_at = event.occurred_at if payment_status is PaymentStatus.PAID else None
            failed_at = (
                event.occurred_at
                if payment_status in {PaymentStatus.FAILED, PaymentStatus.EXPIRED}
                else None
            )
            cancelled_at = (
                event.occurred_at
                if (payment_status is PaymentStatus.CANCELLED or event.provider_status == "DELETED")
                else None
            )
            await self.connection.execute(
                """
                update order_payments
                set provider_status = %s,
                    paid_at = coalesce(paid_at, %s),
                    failed_at = %s,
                    cancelled_at = %s,
                    updated_at = %s,
                    last_checked_at = %s,
                    confirmed_at = case when %s in ('CONFIRMED', 'RECEIVED')
                      and %s < requested_expires_at then coalesce(confirmed_at, %s)
                      else confirmed_at end,
                    review_reason = case when %s = 'review_required'
                      then 'late_or_inconsistent_payment' else review_reason end
                where provider = %s and provider_payment_id = %s
                """,
                (
                    event.provider_status,
                    paid_at,
                    failed_at,
                    cancelled_at,
                    event.occurred_at,
                    event.occurred_at,
                    event.provider_status,
                    event.occurred_at,
                    event.occurred_at,
                    payment_status.value,
                    event.provider,
                    event.provider_payment_id,
                ),
            )
            await self.connection.execute(
                """
                update orders
                set payment_status = %s, updated_at = %s,
                    payment_method = 'pix'
                where id = %s and (payment_method = 'pix' or %s = 'review_required')
                """,
                (payment_status.value, event.occurred_at, row["order_id"], payment_status.value),
            )
            return True

    async def enqueue_event(self, event: PaymentEvent) -> None:
        payload = asdict(event)
        payload["occurred_at"] = event.occurred_at.isoformat()
        await self.connection.execute(
            """insert into payment_event_inbox (provider, event_id, payload)
               values (%s, %s, %s) on conflict do nothing""",
            (event.provider, event.id, Jsonb(payload)),
        )
        # Do not acknowledge HTTP delivery until receipt is durable.
        await self.connection.commit()

    async def pending_events(self, limit: int = 20) -> list[PaymentEvent]:
        result = await self.connection.execute(
            """select payload from payment_event_inbox
               where processed_at is null and next_attempt_at <= now()
               order by next_attempt_at limit %s""",
            (limit,),
        )
        events = []
        for row in await result.fetchall():
            data = dict(row["payload"])
            data["occurred_at"] = datetime.fromisoformat(data["occurred_at"])
            events.append(PaymentEvent(**data))
        return events

    async def complete_event(self, event: PaymentEvent) -> None:
        await self.connection.execute(
            """update payment_event_inbox set processed_at = now(), last_error = null
               where provider = %s and event_id = %s""",
            (event.provider, event.id),
        )

    async def retry_event(self, event: PaymentEvent, error_code: str) -> None:
        await self.connection.execute(
            """update payment_event_inbox set attempts = attempts + 1, last_error = %s,
                 next_attempt_at = now() + least(300, 5 * (attempts + 1)) * interval '1 second'
               where provider = %s and event_id = %s and processed_at is null""",
            (error_code, event.provider, event.id),
        )

    async def reconciliation_candidates(self) -> list[UUID]:
        result = await self.connection.execute(
            """select o.id as order_id from orders o
               left join order_payments p on o.id = p.order_id
               where o.payment_method = 'pix' and (
                 (p.id is null and o.payment_status = 'pending' and o.cutoff_at <= now())
                 or (p.provider = 'asaas' and p.cancelled_at is null
                 and o.payment_status in ('pending', 'processing', 'expired', 'failed')
                 and (p.last_checked_at is null
                      or p.last_checked_at < now() - interval '5 minutes'
                      or p.requested_expires_at <= now()))
               )
               order by p.last_checked_at nulls first limit 20""",
        )
        return [row["order_id"] for row in await result.fetchall()]

    async def expire_unfunded(self, order_id: UUID, now: datetime) -> None:
        await self.connection.execute(
            """update orders set payment_status = 'expired', updated_at = %s
               where id = %s and payment_method = 'pix' and payment_status = 'pending'
                 and cutoff_at <= %s""",
            (now, order_id, now),
        )

    async def switch_order_to_delivery(self, order_id: UUID, changed_at: datetime) -> None:
        async with self.connection.transaction():
            await self.connection.execute(
                """
                update order_payments
                set provider_status = 'canceled', cancelled_at = %s, updated_at = %s
                where order_id = %s and paid_at is null
                """,
                (changed_at, changed_at, order_id),
            )
            await self.connection.execute(
                """
                update orders
                set payment_method = 'pay_on_delivery',
                    payment_status = 'not_applicable',
                    updated_at = %s
                where id = %s and payment_method = 'pix'
                """,
                (changed_at, order_id),
            )

    async def cancel_pix(self, order_id: UUID, changed_at: datetime) -> None:
        async with self.connection.transaction():
            await self.connection.execute(
                """
                update order_payments
                set provider_status = 'canceled', cancelled_at = %s, updated_at = %s
                where order_id = %s and paid_at is null
                """,
                (changed_at, changed_at, order_id),
            )
            await self.connection.execute(
                """
                update orders
                set payment_status = 'cancelled', updated_at = %s
                where id = %s and payment_method = 'pix' and payment_status <> 'paid'
                """,
                (changed_at, order_id),
            )
