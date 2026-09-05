import asyncio
import logging
from datetime import UTC, datetime

from app.modules.payments.api.dependencies import build_payment_service
from app.modules.payments.infrastructure.repository import PostgresPaymentRepository

logger = logging.getLogger(__name__)


async def payment_worker(database, settings) -> None:
    """Durable inbox retries and cutoff sweep; safe to run in multiple API processes."""
    while True:
        try:
            await process_batch(database, settings)
        except Exception as error:
            logger.error("Payment worker batch failed: %s", type(error).__name__)
        await asyncio.sleep(settings.payment_worker_interval_seconds)


async def process_batch(database, settings) -> None:
    async with database.pool.connection() as connection:
        repository = PostgresPaymentRepository(connection)
        events = await repository.pending_events()
        candidates = await repository.reconciliation_candidates()
    for event in events:
        try:
            async with database.pool.connection() as connection:
                service = build_payment_service(settings, connection)
                await service.process_payment_event(event)
                await service.payments.complete_event(event)
            logger.info("Payment event processed: provider=%s event=%s", event.provider, event.id)
        except Exception as error:
            code = getattr(error, "code", type(error).__name__)
            async with database.pool.connection() as connection:
                await PostgresPaymentRepository(connection).retry_event(event, code)
            logger.warning("Payment event retry: event=%s code=%s", event.id, code)
    for order_id in candidates:
        try:
            async with database.pool.connection() as connection:
                await build_payment_service(settings, connection).reconcile_order(
                    order_id, datetime.now(UTC)
                )
        except Exception as error:
            logger.warning(
                "Payment reconciliation retry: order=%s code=%s",
                order_id,
                getattr(error, "code", type(error).__name__),
            )
