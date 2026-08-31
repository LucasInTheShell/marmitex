from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.modules.auth.api.dependencies import current_account
from app.modules.auth.domain.entities import Account, AccountRole
from app.modules.orders.api.dependencies import (
    cancel_order_use_case,
    create_order_use_case,
    order_service,
)
from app.modules.orders.domain.entities import (
    CompanyMealTimeProductionSummary,
    CompanyProductionSummary,
    DailyProductionSummary,
    MealTimeProductionSummary,
    Order,
    OrderItem,
    ProductionItemSummary,
    ProductionSizeSummary,
    ProductionStatus,
)
from tests.test_health import FakeDatabase

NOW = datetime.fromisoformat("2026-08-31T09:00:00-03:00")


def sample_order(company_id: UUID) -> Order:
    return Order(
        id=uuid4(),
        order_number=81,
        company_id=company_id,
        company_name="Empresa Teste",
        date=date(2026, 8, 31),
        meal_schedule_id=uuid4(),
        meal_schedule_label="Almoço",
        scheduled_for=datetime.fromisoformat("2026-08-31T13:00:00-03:00"),
        cutoff_at=datetime.fromisoformat("2026-08-31T11:30:00-03:00"),
        employee_name="Maria da Silva",
        employee_phone="11999998888",
        employee_department="Financeiro",
        employee_cpf="12345678901",
        employee_internal_id="1042",
        production_status=ProductionStatus.PENDING,
        total_price=Decimal("49.80"),
        idempotency_key="checkout-81",
        request_fingerprint="a" * 64,
        created_at=NOW,
        updated_at=NOW,
        cancelled_at=None,
        cancellation_reason=None,
        items=[
            OrderItem(
                id=uuid4(),
                menu_item_id=uuid4(),
                item_name="Frango grelhado",
                item_description="Com salada",
                size="M",
                quantity=2,
                unit_price=Decimal("24.90"),
                subtotal=Decimal("49.80"),
                notes="Sem cebola",
            )
        ],
    )


def authenticated_account(role: AccountRole, company_id: UUID | None = None) -> Account:
    return Account(
        id=uuid4(),
        name="Conta",
        email="conta@example.com",
        company_id=company_id,
        role=role,
    )


class FakeCreateOrder:
    def __init__(self, order: Order) -> None:
        self.order = order
        self.command = None

    async def execute(self, command, now, time_zone):
        self.command = command
        return self.order


class FakeCancelOrder:
    def __init__(self, order: Order) -> None:
        self.order = order
        self.arguments = None

    async def execute(self, *arguments):
        self.arguments = arguments
        return self.order


class FakeOrderService:
    def __init__(self, order: Order) -> None:
        self.order = order
        self.list_arguments = None
        self.status_arguments = None

    async def list(self, *arguments):
        self.list_arguments = arguments
        return [self.order]

    async def production_board(self, board_date):
        return [self.order]

    async def production_summary(self, summary_date, time_zone):
        item = self.order.items[0]
        return DailyProductionSummary(
            date=summary_date,
            total_orders=1,
            total_meals=item.quantity,
            meal_times=[
                MealTimeProductionSummary(
                    scheduled_for=self.order.scheduled_for,
                    meal_time=time(13),
                    schedule_ids=[self.order.meal_schedule_id],
                    schedule_labels=[self.order.meal_schedule_label],
                    total_orders=1,
                    total_meals=item.quantity,
                    items=[
                        ProductionItemSummary(
                            menu_item_id=item.menu_item_id,
                            item_name=item.item_name,
                            total_quantity=item.quantity,
                            sizes=[ProductionSizeSummary(size=item.size, quantity=item.quantity)],
                        )
                    ],
                )
            ],
            companies=[
                CompanyProductionSummary(
                    company_id=self.order.company_id,
                    company_name=self.order.company_name,
                    total_orders=1,
                    total_meals=item.quantity,
                    meal_times=[
                        CompanyMealTimeProductionSummary(
                            scheduled_for=self.order.scheduled_for,
                            meal_time=time(13),
                            total_orders=1,
                            total_meals=item.quantity,
                        )
                    ],
                    items=[
                        ProductionItemSummary(
                            menu_item_id=item.menu_item_id,
                            item_name=item.item_name,
                            total_quantity=item.quantity,
                            sizes=[
                                ProductionSizeSummary(
                                    size=item.size, quantity=item.quantity
                                )
                            ],
                        )
                    ],
                )
            ],
        )

    async def by_id(self, order_id, company_id=None):
        return self.order

    async def update_production_status(self, *arguments):
        self.status_arguments = arguments
        return self.order


def order_test_app(
    account: Account,
    *,
    create_use_case: FakeCreateOrder | None = None,
    cancel_use_case: FakeCancelOrder | None = None,
    service: FakeOrderService | None = None,
):
    app = create_app(
        Settings(database_url="postgresql://local/test"),
        FakeDatabase(),  # type: ignore[arg-type]
    )
    app.dependency_overrides[current_account] = lambda: account
    if create_use_case:
        app.dependency_overrides[create_order_use_case] = lambda: create_use_case
    if cancel_use_case:
        app.dependency_overrides[cancel_order_use_case] = lambda: cancel_use_case
    if service:
        app.dependency_overrides[order_service] = lambda: service
    return app


def create_payload(order: Order) -> dict:
    return {
        "date": "2026-08-31",
        "meal_schedule_id": str(order.meal_schedule_id),
        "employee_name": "Maria da Silva",
        "employee_phone": "(11) 99999-8888",
        "employee_department": "Financeiro",
        "employee_cpf": "123.456.789-01",
        "employee_internal_id": "1042",
        "items": [
            {
                "menu_item_id": str(order.items[0].menu_item_id),
                "size": "M",
                "quantity": 2,
                "notes": "Sem cebola",
            }
        ],
    }


def test_company_creates_multi_item_order_with_company_from_session() -> None:
    company_id = uuid4()
    order = sample_order(company_id)
    use_case = FakeCreateOrder(order)
    account = authenticated_account(AccountRole.COMPANY, company_id)
    app = order_test_app(account, create_use_case=use_case)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/orders",
            json=create_payload(order),
            headers={"Idempotency-Key": "checkout-81"},
        )

    assert response.status_code == 201
    assert response.json()["order_number"] == 81
    assert response.json()["items"][0]["quantity"] == 2
    assert response.json()["total_price"] == 49.8
    assert "request_fingerprint" not in response.json()
    assert use_case.command.company_id == company_id
    assert use_case.command.idempotency_key == "checkout-81"


def test_admin_cannot_create_company_order() -> None:
    order = sample_order(uuid4())
    app = order_test_app(
        authenticated_account(AccountRole.ADMIN),
        create_use_case=FakeCreateOrder(order),
    )

    with TestClient(app) as client:
        response = client.post("/api/v1/orders", json=create_payload(order))

    assert response.status_code == 403


def test_company_list_is_always_scoped_to_its_session() -> None:
    company_id = uuid4()
    service = FakeOrderService(sample_order(company_id))
    app = order_test_app(authenticated_account(AccountRole.COMPANY, company_id), service=service)

    with TestClient(app) as client:
        response = client.get("/api/v1/orders?start=2026-08-31&end=2026-08-31")

    assert response.status_code == 200
    assert service.list_arguments[2] == company_id

    with TestClient(app) as client:
        forbidden = client.get(
            f"/api/v1/orders?start=2026-08-31&end=2026-08-31&company_id={uuid4()}"
        )

    assert forbidden.status_code == 403


def test_kitchen_board_does_not_expose_cpf_or_phone() -> None:
    service = FakeOrderService(sample_order(uuid4()))
    app = order_test_app(authenticated_account(AccountRole.KITCHEN), service=service)

    with TestClient(app) as client:
        response = client.get("/api/v1/kitchen/production-board?date=2026-08-31")

    assert response.status_code == 200
    payload = response.json()[0]
    assert payload["employee_name"] == "Maria da Silva"
    assert "employee_cpf" not in payload
    assert "employee_phone" not in payload
    assert "cutoff_at" not in payload


def test_kitchen_reads_production_summary_grouped_by_meal_time() -> None:
    service = FakeOrderService(sample_order(uuid4()))
    app = order_test_app(authenticated_account(AccountRole.KITCHEN), service=service)

    with TestClient(app) as client:
        response = client.get("/api/v1/kitchen/production-summary?date=2026-08-31")

    assert response.status_code == 200
    payload = response.json()
    assert payload["date"] == "2026-08-31"
    assert payload["total_orders"] == 1
    assert payload["total_meals"] == 2
    assert payload["meal_times"][0]["meal_time"] == "13:00:00"
    assert payload["meal_times"][0]["items"][0] == {
        "menu_item_id": str(service.order.items[0].menu_item_id),
        "item_name": "Frango grelhado",
        "total_quantity": 2,
        "sizes": [{"size": "M", "quantity": 2}],
    }
    assert payload["companies"][0]["company_name"] == "Empresa Teste"
    assert payload["companies"][0]["meal_times"][0]["total_meals"] == 2


def test_only_kitchen_or_admin_updates_production_status() -> None:
    company_id = uuid4()
    order = sample_order(company_id)
    company_service = FakeOrderService(order)
    company_app = order_test_app(
        authenticated_account(AccountRole.COMPANY, company_id),
        service=company_service,
    )

    with TestClient(company_app) as client:
        forbidden = client.patch(
            f"/api/v1/orders/{order.id}/status",
            json={"production_status": "printed"},
        )

    assert forbidden.status_code == 403

    kitchen_service = FakeOrderService(order)
    kitchen_app = order_test_app(
        authenticated_account(AccountRole.KITCHEN), service=kitchen_service
    )
    with TestClient(kitchen_app) as client:
        updated = client.patch(
            f"/api/v1/orders/{order.id}/status",
            json={"production_status": "printed"},
        )

    assert updated.status_code == 200
    assert kitchen_service.status_arguments[1] is ProductionStatus.PRINTED


def test_company_cancels_order_using_authenticated_identifiers() -> None:
    company_id = uuid4()
    account = authenticated_account(AccountRole.COMPANY, company_id)
    order = sample_order(company_id)
    use_case = FakeCancelOrder(order)
    app = order_test_app(account, cancel_use_case=use_case)

    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/orders/{order.id}/cancel",
            json={"reason": "Pedido duplicado"},
        )

    assert response.status_code == 200
    assert use_case.arguments[0] == order.id
    assert use_case.arguments[1] == company_id
    assert use_case.arguments[2] == account.id
