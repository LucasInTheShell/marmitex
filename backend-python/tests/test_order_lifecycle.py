from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.modules.orders.application.cancel_order import CancelOrder
from app.modules.orders.application.services import OrderApplicationService
from app.modules.orders.domain.entities import (
    Order,
    OrderItem,
    PaymentMethod,
    PaymentStatus,
    ProductionStatus,
)
from app.modules.orders.domain.exceptions import (
    InvalidOrderPeriodError,
    InvalidProductionStatusTransitionError,
    OrderCannotBeCancelledError,
)

NOW = datetime.fromisoformat("2026-08-31T09:00:00-03:00")


def pending_order() -> Order:
    company_id = uuid4()
    return Order(
        id=uuid4(),
        order_number=7,
        company_id=company_id,
        company_name="Empresa",
        date=date(2026, 8, 31),
        meal_schedule_id=uuid4(),
        meal_schedule_label="Almoço",
        scheduled_for=datetime.fromisoformat("2026-08-31T13:00:00-03:00"),
        cutoff_at=datetime.fromisoformat("2026-08-31T11:30:00-03:00"),
        employee_name="Maria",
        employee_phone="11999998888",
        employee_department="Financeiro",
        employee_cpf="12345678901",
        employee_internal_id=None,
        production_status=ProductionStatus.PENDING,
        total_price=Decimal("20.00"),
        idempotency_key=None,
        request_fingerprint=None,
        created_at=NOW,
        updated_at=NOW,
        cancelled_at=None,
        cancellation_reason=None,
        items=[],
    )


class FakeLifecycleRepository:
    def __init__(self, order: Order) -> None:
        self.order = order
        self.list_arguments = None

    async def by_id(self, order_id: UUID, *, for_update: bool = False) -> Order | None:
        return self.order if order_id == self.order.id else None

    async def cancel(
        self,
        order_id: UUID,
        company_id: UUID,
        account_id: UUID,
        reason: str | None,
        cancelled_at: datetime,
    ) -> bool:
        if order_id != self.order.id or company_id != self.order.company_id:
            return False
        self.order = replace(
            self.order,
            production_status=ProductionStatus.CANCELLED,
            cancelled_at=cancelled_at,
            cancellation_reason=reason,
            updated_at=cancelled_at,
        )
        return True

    async def update_status(
        self,
        order_id: UUID,
        expected_status: ProductionStatus,
        new_status: ProductionStatus,
        changed_at: datetime,
    ) -> bool:
        if order_id != self.order.id or self.order.production_status is not expected_status:
            return False
        self.order = replace(self.order, production_status=new_status, updated_at=changed_at)
        return True

    async def list(
        self,
        start,
        end,
        company_id=None,
        production_status=None,
        *,
        active_only=False,
    ):
        self.list_arguments = (
            start,
            end,
            company_id,
            production_status,
            active_only,
        )
        return [self.order]


@pytest.mark.asyncio
async def test_company_cancels_own_pending_order_before_cutoff() -> None:
    repository = FakeLifecycleRepository(pending_order())
    use_case = CancelOrder(repository)  # type: ignore[arg-type]

    cancelled = await use_case.execute(
        repository.order.id,
        repository.order.company_id,
        uuid4(),
        NOW,
        " Pedido duplicado ",
    )

    assert cancelled.production_status is ProductionStatus.CANCELLED
    assert cancelled.cancellation_reason == "Pedido duplicado"


@pytest.mark.asyncio
async def test_company_cannot_cancel_at_or_after_cutoff() -> None:
    repository = FakeLifecycleRepository(pending_order())
    use_case = CancelOrder(repository)  # type: ignore[arg-type]

    with pytest.raises(OrderCannotBeCancelledError):
        await use_case.execute(
            repository.order.id,
            repository.order.company_id,
            uuid4(),
            datetime.fromisoformat("2026-08-31T11:30:00-03:00"),
        )


@pytest.mark.asyncio
async def test_kitchen_status_follows_the_defined_sequence() -> None:
    repository = FakeLifecycleRepository(pending_order())
    service = OrderApplicationService(repository)  # type: ignore[arg-type]

    printed = await service.update_production_status(
        repository.order.id, ProductionStatus.PRINTED, NOW
    )
    separated = await service.update_production_status(
        repository.order.id, ProductionStatus.SEPARATED, NOW
    )
    delivered = await service.update_production_status(
        repository.order.id, ProductionStatus.DELIVERED, NOW
    )

    assert printed.production_status is ProductionStatus.PRINTED
    assert separated.production_status is ProductionStatus.SEPARATED
    assert delivered.production_status is ProductionStatus.DELIVERED


@pytest.mark.asyncio
async def test_kitchen_cannot_skip_a_production_status() -> None:
    repository = FakeLifecycleRepository(pending_order())
    service = OrderApplicationService(repository)  # type: ignore[arg-type]

    with pytest.raises(InvalidProductionStatusTransitionError):
        await service.update_production_status(repository.order.id, ProductionStatus.DELIVERED, NOW)


@pytest.mark.asyncio
async def test_order_listing_limits_period_to_31_days() -> None:
    repository = FakeLifecycleRepository(pending_order())
    service = OrderApplicationService(repository)  # type: ignore[arg-type]

    with pytest.raises(InvalidOrderPeriodError):
        await service.list(date(2026, 8, 1), date(2026, 9, 1))


@pytest.mark.asyncio
async def test_production_board_includes_delivered_and_excludes_cancelled_orders() -> None:
    delivered = replace(pending_order(), production_status=ProductionStatus.DELIVERED)
    repository = FakeLifecycleRepository(delivered)
    service = OrderApplicationService(repository)  # type: ignore[arg-type]

    board = await service.production_board(date(2026, 8, 31))

    assert board == [delivered]
    assert repository.list_arguments == (
        date(2026, 8, 31),
        date(2026, 8, 31),
        None,
        None,
        False,
    )

    repository.order = replace(delivered, production_status=ProductionStatus.CANCELLED)
    assert await service.production_board(date(2026, 8, 31)) == []


@pytest.mark.asyncio
async def test_production_board_excludes_pix_until_payment_is_confirmed() -> None:
    unpaid = replace(
        pending_order(),
        payment_method=PaymentMethod.PIX,
        payment_status=PaymentStatus.PENDING,
    )
    repository = FakeLifecycleRepository(unpaid)
    service = OrderApplicationService(repository)  # type: ignore[arg-type]

    assert await service.production_board(date(2026, 8, 31)) == []

    repository.order = replace(unpaid, payment_status=PaymentStatus.PAID)
    assert await service.production_board(date(2026, 8, 31)) == [repository.order]


class FakeSummaryRepository:
    def __init__(self, orders: list[Order]) -> None:
        self.orders = orders

    async def list(self, *_, **__) -> list[Order]:
        return self.orders


def order_item(name: str, quantity: int, size: str = "M") -> OrderItem:
    unit_price = Decimal("20.00")
    return OrderItem(
        id=uuid4(),
        menu_item_id=uuid4(),
        item_name=name,
        item_description=None,
        size=size,
        quantity=quantity,
        unit_price=unit_price,
        subtotal=unit_price * quantity,
        notes=None,
    )


@pytest.mark.asyncio
async def test_production_summary_groups_companies_by_meal_time_and_dish() -> None:
    parmegiana = order_item("Parmegiana de frango", 10, "M")
    feijoada = order_item("Feijoada", 10, "G")
    first = replace(
        pending_order(),
        scheduled_for=datetime.fromisoformat("2026-08-31T11:00:00-03:00"),
        items=[parmegiana, feijoada],
    )
    second_parmegiana = replace(
        parmegiana,
        id=uuid4(),
        size="G",
        quantity=10,
        subtotal=Decimal("200.00"),
    )
    second = replace(
        pending_order(),
        scheduled_for=datetime.fromisoformat("2026-08-31T11:00:00-03:00"),
        items=[second_parmegiana],
    )
    lasagna = order_item("Lasanha", 10, "P")
    third = replace(
        pending_order(),
        scheduled_for=datetime.fromisoformat("2026-08-31T11:30:00-03:00"),
        items=[lasagna],
    )
    cancelled = replace(
        pending_order(),
        production_status=ProductionStatus.CANCELLED,
        scheduled_for=datetime.fromisoformat("2026-08-31T11:00:00-03:00"),
        items=[order_item("Não deve contar", 10)],
    )
    repository = FakeSummaryRepository([first, second, third, cancelled])
    service = OrderApplicationService(repository)  # type: ignore[arg-type]

    summary = await service.production_summary(
        date(2026, 8, 31), "America/Sao_Paulo"
    )

    assert summary.total_orders == 3
    assert summary.total_meals == 40
    assert [group.meal_time.isoformat() for group in summary.meal_times] == [
        "11:00:00",
        "11:30:00",
    ]
    eleven = summary.meal_times[0]
    assert eleven.total_orders == 2
    assert eleven.total_meals == 30
    assert [(item.item_name, item.total_quantity) for item in eleven.items] == [
        ("Parmegiana de frango", 20),
        ("Feijoada", 10),
    ]
    assert [(size.size, size.quantity) for size in eleven.items[0].sizes] == [
        ("M", 10),
        ("G", 10),
    ]
    assert summary.companies[0].company_name == "Empresa"
    assert sum(company.total_orders for company in summary.companies) == 3
    assert sum(company.total_meals for company in summary.companies) == 40


@pytest.mark.asyncio
async def test_production_summary_converts_database_utc_to_operational_timezone() -> None:
    order = replace(
        pending_order(),
        scheduled_for=datetime.fromisoformat("2026-08-31T16:00:00+00:00"),
        items=[order_item("Frango", 1)],
    )
    service = OrderApplicationService(FakeSummaryRepository([order]))  # type: ignore[arg-type]

    summary = await service.production_summary(
        date(2026, 8, 31), "America/Sao_Paulo"
    )

    assert summary.meal_times[0].meal_time.isoformat() == "13:00:00"
    assert summary.companies[0].meal_times[0].meal_time.isoformat() == "13:00:00"
