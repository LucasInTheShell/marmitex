"""Opt-in PostgreSQL tests. Only a newly created, random test database is modified."""

import asyncio
import os
import re
import sys
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import make_conninfo
from psycopg.rows import dict_row

from app.modules.orders.infrastructure.repository import PostgresOrderRepository
from app.modules.payments.application.services import PaymentApplicationService
from app.modules.payments.infrastructure.repository import PostgresPaymentRepository
from tests.test_asaas_gateway import event_for
from tests.test_payments import CUTOFF, NOW, FakeCompanyRepository, FakePaymentGateway, pix_order


@pytest.fixture(scope="module")
def event_loop_policy():
    if sys.platform == "win32":
        return asyncio.WindowsSelectorEventLoopPolicy()
    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture(scope="module")
def payment_database():
    admin_url = os.environ.get("PAYMENT_TEST_ADMIN_URL")
    if not admin_url:
        pytest.skip("Set PAYMENT_TEST_ADMIN_URL to run isolated PostgreSQL payment tests")
    name = "mavi_payment_test_" + uuid4().hex
    with psycopg.connect(admin_url, autocommit=True) as admin:
        admin.execute(sql.SQL("create database {}").format(sql.Identifier(name)))
        try:
            url = make_conninfo(admin_url, dbname=name)
            with psycopg.connect(url, autocommit=True) as connection:
                for migration in sorted((Path(__file__).parents[2] / "migrations").glob("*.sql")):
                    source = re.sub(r"--[^\n]*", "", migration.read_text(encoding="utf-8"))
                    if "$$" in source:
                        connection.execute(source, prepare=False)
                        continue
                    for statement in source.split(";"):
                        if statement.strip():
                            connection.execute(statement)
            yield url
        finally:
            assert name.startswith("mavi_payment_test_")
            admin.execute(sql.SQL("drop database {} with (force)").format(sql.Identifier(name)))


async def seed(url):
    order = pix_order()
    async with await psycopg.AsyncConnection.connect(url, row_factory=dict_row) as connection:
        await connection.execute(
            "insert into companies (id, name) values (%s, %s)",
            (order.company_id, order.company_name),
        )
        await connection.execute(
            """insert into orders (id, company_id, date, employee_name, employee_phone,
                   employee_department, employee_cpf, total_price, cutoff_at,
                   payment_method, payment_status)
               values (%s,%s,%s,%s,%s,%s,%s,%s,%s,'pix','pending')""",
            (
                order.id,
                order.company_id,
                order.date,
                order.employee_name,
                order.employee_phone,
                order.employee_department,
                order.employee_cpf,
                order.total_price,
                order.cutoff_at,
            ),
        )
    return order


def make_service(connection, order, adapter):
    return PaymentApplicationService(
        PostgresOrderRepository(connection),
        FakeCompanyRepository(order),
        PostgresPaymentRepository(connection),
        adapter,
    )


async def test_concurrent_checkouts_create_one_charge(payment_database):
    order = await seed(payment_database)

    class SlowGateway(FakePaymentGateway):
        async def create_pix_payment(self, **kwargs):
            await asyncio.sleep(0.1)
            return await super().create_pix_payment(**kwargs)

    adapter = SlowGateway()

    async def checkout():
        async with await psycopg.AsyncConnection.connect(
            payment_database, row_factory=dict_row
        ) as c:
            return await make_service(c, order, adapter).pix_checkout(
                order.id, order.company_id, NOW
            )

    first, second = await asyncio.wait_for(asyncio.gather(checkout(), checkout()), timeout=10)
    assert first.provider_payment_id == second.provider_payment_id
    assert len(adapter.created) == 1


async def test_durable_inbox_duplicate_and_refund_terminal_state(payment_database):
    order = await seed(payment_database)
    # Use a unique provider id per fixture; the database retains all tests in this module.
    payment_id = "pay_" + order.id.hex
    adapter = FakePaymentGateway()
    adapter.order_id = order.id
    event = replace(event_for(order), id="evt_" + order.id.hex, provider_payment_id=payment_id)
    async with await psycopg.AsyncConnection.connect(payment_database, row_factory=dict_row) as c:
        repo = PostgresPaymentRepository(c)
        await repo.enqueue_event(event)
        await repo.enqueue_event(event)
    async with await psycopg.AsyncConnection.connect(payment_database, row_factory=dict_row) as c:
        repo = PostgresPaymentRepository(c)
        assert len(await repo.pending_events()) == 1
        app = make_service(c, order, adapter)
        adapter.status = "RECEIVED"
        # No local payment exists: simulate webhook preceding local commit/rollback.
        assert await app.process_payment_event(event, NOW)
        await repo.complete_event(event)
        assert not await app.process_payment_event(event, NOW)
        adapter.status = "REFUNDED"
        await app.process_payment_event(replace(event, id=event.id + "_refund"), NOW)
        adapter.status = "RECEIVED"
        await app.process_payment_event(replace(event, id=event.id + "_stale"), NOW)
        saved = await app.orders.by_id(order.id)
        assert saved.payment_status.value == "refunded"
        assert (await repo.by_order_id(order.id)).paid_at is not None
    async with await psycopg.AsyncConnection.connect(payment_database, row_factory=dict_row) as c:
        assert not await PostgresPaymentRepository(c).pending_events()


async def test_cutoff_removal_is_persisted_and_not_repeated(payment_database):
    order = await seed(payment_database)
    adapter = FakePaymentGateway()
    adapter.order_id = order.id
    payment_id = "pay_" + order.id.hex
    async with await psycopg.AsyncConnection.connect(payment_database, row_factory=dict_row) as c:
        repo = PostgresPaymentRepository(c)
        await repo.create(order.id, "asaas", payment_id, "PENDING", 2490, "brl", CUTOFF)
        await make_service(c, order, adapter).reconcile_order(order.id, CUTOFF)
    async with await psycopg.AsyncConnection.connect(payment_database, row_factory=dict_row) as c:
        repo = PostgresPaymentRepository(c)
        saved = await PostgresOrderRepository(c).by_id(order.id)
        assert saved.payment_status.value == "expired"
        assert (await repo.by_order_id(order.id)).cancelled_at is not None
        assert order.id not in await repo.reconciliation_candidates()


async def test_worker_retries_failed_event_without_losing_it(payment_database, monkeypatch):
    from app.core.config import Settings
    from app.core.database import Database
    from app.modules.payments.infrastructure import worker

    order = await seed(payment_database)
    event = replace(event_for(order), id="evt_retry_" + order.id.hex)
    async with await psycopg.AsyncConnection.connect(payment_database, row_factory=dict_row) as c:
        await PostgresPaymentRepository(c).enqueue_event(event)

    class FailingService:
        async def process_payment_event(self, event):
            raise RuntimeError("simulated network failure")

        async def reconcile_order(self, order_id, now):
            return None

    monkeypatch.setattr(worker, "build_payment_service", lambda *args: FailingService())
    settings = Settings(database_url="postgresql://unused/test")
    # The test DSN is generated by this module, not the application's database.
    settings.database_url = payment_database
    database = Database(settings)
    await database.open()
    try:
        await worker.process_batch(database, settings)
    finally:
        await database.close()
    async with await psycopg.AsyncConnection.connect(payment_database, row_factory=dict_row) as c:
        result = await c.execute(
            "select attempts, processed_at, last_error from payment_event_inbox "
            "where event_id = %s",
            (event.id,),
        )
        row = await result.fetchone()
        assert row["attempts"] == 1
        assert row["processed_at"] is None
        assert row["last_error"] == "RuntimeError"
