from dataclasses import replace
from datetime import UTC, date, datetime, time
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.modules.companies.domain.entities import Company, MealSchedule
from app.modules.menus.domain.entities import AvailableMenu, MenuItem
from app.modules.operations.domain.entities import OperationalSettings
from app.modules.orders.application.create_order import (
    CreateOrder,
    CreateOrderCommand,
    RequestedOrderItem,
)
from app.modules.orders.domain.entities import (
    Order,
    OrderDraft,
    OrderItem,
    PaymentMethod,
    PaymentStatus,
    ProductionStatus,
)
from app.modules.orders.domain.exceptions import (
    IdempotencyConflictError,
    MenuItemUnavailableError,
    OrderingWindowClosedError,
)

NOW = datetime.fromisoformat("2026-08-31T09:00:00-03:00")
ORDER_DATE = date(2026, 8, 31)


class FakeOrderRepository:
    def __init__(self) -> None:
        self.created_drafts: list[OrderDraft] = []
        self.orders_by_key: dict[tuple[UUID, str], Order] = {}

    async def by_idempotency_key(self, company_id: UUID, idempotency_key: str) -> Order | None:
        return self.orders_by_key.get((company_id, idempotency_key))

    async def create(self, draft: OrderDraft) -> Order:
        self.created_drafts.append(draft)
        order = order_from_draft(draft)
        if draft.idempotency_key:
            self.orders_by_key[(draft.company_id, draft.idempotency_key)] = order
        return order


class FakeCompanyRepository:
    def __init__(self, company: Company) -> None:
        self.company = company

    async def by_id(self, company_id: UUID) -> Company | None:
        return self.company if self.company.id == company_id else None


class FakeMenuRepository:
    def __init__(self, menu: AvailableMenu) -> None:
        self.menu = menu

    async def published_between(self, start: date, end: date) -> list[AvailableMenu]:
        if start <= self.menu.date <= end:
            return [self.menu]
        return []


class FakeSettingsRepository:
    async def get(self) -> OperationalSettings:
        return OperationalSettings(
            order_cutoff_lead_minutes=90,
            updated_at=datetime(2026, 8, 1, tzinfo=UTC),
        )


def company_and_schedule() -> tuple[Company, MealSchedule]:
    company_id = uuid4()
    schedule = MealSchedule(
        id=uuid4(),
        company_id=company_id,
        label="Almoço",
        meal_time=time(13),
        weekdays=[1, 2, 3, 4, 5],
        active=True,
        sort_order=0,
    )
    return (
        Company(
            id=company_id,
            name="Empresa Teste",
            active=True,
            created_at=datetime(2026, 8, 1, tzinfo=UTC),
            access_email="empresa@example.com",
            meal_schedules=[schedule],
        ),
        schedule,
    )


def menu(*items: MenuItem) -> AvailableMenu:
    return AvailableMenu(date=ORDER_DATE, items=list(items), available_schedules=[])


def command(
    company_id: UUID,
    schedule_id: UUID,
    items: list[RequestedOrderItem],
    *,
    idempotency_key: str | None = None,
    payment_method: PaymentMethod = PaymentMethod.PAY_ON_DELIVERY,
) -> CreateOrderCommand:
    return CreateOrderCommand(
        company_id=company_id,
        date=ORDER_DATE,
        meal_schedule_id=schedule_id,
        employee_name="  Maria da Silva  ",
        employee_phone="(11) 99999-8888",
        employee_department="  Financeiro  ",
        employee_cpf="123.456.789-01",
        employee_internal_id=" 1042 ",
        items=items,
        idempotency_key=idempotency_key,
        payment_method=payment_method,
    )


def order_from_draft(draft: OrderDraft) -> Order:
    created_at = NOW
    return Order(
        id=uuid4(),
        order_number=42,
        company_id=draft.company_id,
        company_name="Empresa Teste",
        date=draft.date,
        meal_schedule_id=draft.meal_schedule_id,
        meal_schedule_label=draft.meal_schedule_label,
        scheduled_for=draft.scheduled_for,
        cutoff_at=draft.cutoff_at,
        employee_name=draft.employee_name,
        employee_phone=draft.employee_phone,
        employee_department=draft.employee_department,
        employee_cpf=draft.employee_cpf,
        employee_internal_id=draft.employee_internal_id,
        production_status=ProductionStatus.PENDING,
        total_price=draft.total_price,
        idempotency_key=draft.idempotency_key,
        request_fingerprint=draft.request_fingerprint,
        created_at=created_at,
        updated_at=created_at,
        cancelled_at=None,
        cancellation_reason=None,
        items=[
            OrderItem(
                id=uuid4(),
                menu_item_id=item.menu_item_id,
                item_name=item.item_name,
                item_description=item.item_description,
                size=item.size,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.subtotal,
                notes=item.notes,
            )
            for item in draft.items
        ],
        payment_method=draft.payment_method,
        payment_status=draft.payment_status,
    )


@pytest.mark.asyncio
async def test_create_order_accepts_different_meals_and_snapshots_prices() -> None:
    company, schedule = company_and_schedule()
    chicken = MenuItem(
        id=uuid4(),
        name="Frango grelhado",
        description="Com salada",
        size_options=["M", "G"],
        price=Decimal("24.90"),
    )
    beef = MenuItem(
        id=uuid4(),
        name="Carne de panela",
        description=None,
        size_options=["P", "M"],
        price=Decimal("27.50"),
    )
    repository = FakeOrderRepository()
    use_case = CreateOrder(
        repository,  # type: ignore[arg-type]
        FakeCompanyRepository(company),  # type: ignore[arg-type]
        FakeMenuRepository(menu(chicken, beef)),  # type: ignore[arg-type]
        FakeSettingsRepository(),  # type: ignore[arg-type]
    )

    order = await use_case.execute(
        command(
            company.id,
            schedule.id,
            [
                RequestedOrderItem(chicken.id, "M", 2, " Sem cebola "),
                RequestedOrderItem(beef.id, "P", 1),
            ],
        ),
        NOW,
        "America/Sao_Paulo",
    )

    assert order.total_price == Decimal("77.30")
    assert [item.item_name for item in order.items] == [
        "Frango grelhado",
        "Carne de panela",
    ]
    assert order.items[0].subtotal == Decimal("49.80")
    assert order.items[0].notes == "Sem cebola"
    assert order.employee_cpf == "12345678901"
    assert order.employee_phone == "11999998888"
    assert order.employee_name == "Maria da Silva"
    assert order.meal_schedule_label == "Almoço"
    assert order.cutoff_at == datetime.fromisoformat("2026-08-31T11:30:00-03:00")


@pytest.mark.asyncio
async def test_create_order_rejects_item_outside_published_menu() -> None:
    company, schedule = company_and_schedule()
    published_item = MenuItem(
        id=uuid4(),
        name="Frango",
        description=None,
        size_options=["M"],
        price=Decimal("20.00"),
    )
    use_case = CreateOrder(
        FakeOrderRepository(),  # type: ignore[arg-type]
        FakeCompanyRepository(company),  # type: ignore[arg-type]
        FakeMenuRepository(menu(published_item)),  # type: ignore[arg-type]
        FakeSettingsRepository(),  # type: ignore[arg-type]
    )

    with pytest.raises(MenuItemUnavailableError):
        await use_case.execute(
            command(
                company.id,
                schedule.id,
                [RequestedOrderItem(uuid4(), "M", 1)],
            ),
            NOW,
            "America/Sao_Paulo",
        )


@pytest.mark.asyncio
async def test_create_order_revalidates_cutoff_at_confirmation() -> None:
    company, schedule = company_and_schedule()
    item = MenuItem(
        id=uuid4(),
        name="Frango",
        description=None,
        size_options=["M"],
        price=Decimal("20.00"),
    )
    use_case = CreateOrder(
        FakeOrderRepository(),  # type: ignore[arg-type]
        FakeCompanyRepository(company),  # type: ignore[arg-type]
        FakeMenuRepository(menu(item)),  # type: ignore[arg-type]
        FakeSettingsRepository(),  # type: ignore[arg-type]
    )

    with pytest.raises(OrderingWindowClosedError):
        await use_case.execute(
            command(company.id, schedule.id, [RequestedOrderItem(item.id, "M", 1)]),
            datetime.fromisoformat("2026-08-31T11:30:00-03:00"),
            "America/Sao_Paulo",
        )


@pytest.mark.asyncio
async def test_same_idempotency_key_replays_only_the_same_request() -> None:
    company, schedule = company_and_schedule()
    item = MenuItem(
        id=uuid4(),
        name="Frango",
        description=None,
        size_options=["M", "G"],
        price=Decimal("20.00"),
    )
    repository = FakeOrderRepository()
    use_case = CreateOrder(
        repository,  # type: ignore[arg-type]
        FakeCompanyRepository(company),  # type: ignore[arg-type]
        FakeMenuRepository(menu(item)),  # type: ignore[arg-type]
        FakeSettingsRepository(),  # type: ignore[arg-type]
    )
    first_command = command(
        company.id,
        schedule.id,
        [RequestedOrderItem(item.id, "M", 1)],
        idempotency_key="checkout-123",
    )

    first = await use_case.execute(first_command, NOW, "America/Sao_Paulo")
    replay = await use_case.execute(
        first_command,
        datetime.fromisoformat("2026-08-31T13:00:00-03:00"),
        "America/Sao_Paulo",
    )

    assert replay.id == first.id
    assert len(repository.created_drafts) == 1

    changed = replace(
        first_command,
        items=[RequestedOrderItem(item.id, "G", 1)],
    )
    with pytest.raises(IdempotencyConflictError):
        await use_case.execute(changed, NOW, "America/Sao_Paulo")


@pytest.mark.asyncio
async def test_pix_order_starts_awaiting_payment() -> None:
    company, schedule = company_and_schedule()
    item = MenuItem(
        id=uuid4(),
        name="Frango",
        description=None,
        size_options=["M"],
        price=Decimal("20.00"),
    )
    repository = FakeOrderRepository()
    use_case = CreateOrder(
        repository,  # type: ignore[arg-type]
        FakeCompanyRepository(company),  # type: ignore[arg-type]
        FakeMenuRepository(menu(item)),  # type: ignore[arg-type]
        FakeSettingsRepository(),  # type: ignore[arg-type]
    )

    await use_case.execute(
        command(
            company.id,
            schedule.id,
            [RequestedOrderItem(item.id, "M", 1)],
            payment_method=PaymentMethod.PIX,
        ),
        NOW,
        "America/Sao_Paulo",
    )

    assert repository.created_drafts[0].payment_method is PaymentMethod.PIX
    assert repository.created_drafts[0].payment_status is PaymentStatus.PENDING
