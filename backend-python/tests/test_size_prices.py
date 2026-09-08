from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.modules.auth.domain.entities import AccountRole
from app.modules.menus.domain.entities import MenuItem
from app.modules.orders.application.create_order import CreateOrder, RequestedOrderItem
from app.modules.orders.domain.entities import PaymentMethod
from tests.test_available_menu_route import app_for
from tests.test_create_order import (
    NOW,
    FakeCompanyRepository,
    FakeOrderRepository,
    FakeSettingsRepository,
    command,
    company_and_schedule,
    menu,
)
from tests.test_create_order import FakeMenuRepository as OrderMenuRepository
from tests.test_menu_item_images import FakeMenuRepository, FakeStorage, service
from tests.test_payments import service as payment_service


def test_admin_can_create_edit_and_clear_size_prices_through_multipart():
    repository = FakeMenuRepository()
    app = app_for(AccountRole.ADMIN, service(repository, FakeStorage()))
    with TestClient(app) as client:
        data = {
            "name": "Frango",
            "size_options": ["P", "G"],
            "size_prices": '{"P":"12.99","G":"20.90"}',
        }
        response = client.post("/api/v1/menu-items", data=data)
        assert response.status_code == 201, response.text
        item = response.json()
        assert item["price"] is None
        assert item["size_prices"] == {"P": 12.99, "G": 20.90}
        url = f"/api/v1/menu-items/{item['id']}"
        response = client.put(url, data={**data, "size_prices": '{"P":"14","G":"22"}'})
        assert response.status_code == 200, response.text
        assert response.json()["size_prices"] == {"P": 14, "G": 22}
        # Old clients that omit the new field preserve configured overrides.
        response = client.put(url, data={"name": "Frango", "size_options": ["P", "G"]})
        assert response.status_code == 200
        assert response.json()["size_prices"] == {"P": 14, "G": 22}
        response = client.put(url, data={**data, "price": "18.50", "size_prices": "{}"})
        assert response.status_code == 200
        assert response.json()["size_prices"] == {}
        assert response.json()["price"] == 18.5


@pytest.mark.parametrize(
    "prices",
    [
        '{"P":"-1"}',
        '{"P":"1.001"}',
        '{"P":"NaN"}',
        '{"P":"Infinity"}',
        '{"P":"100000000"}',
        '{"X":"15"}',
        '{"P":null}',
        "[]",
        "invalid",
        '{"P":"10","G":"20"}',
    ],
)
def test_api_rejects_invalid_or_disabled_size_prices(prices):
    repository = FakeMenuRepository()
    app = app_for(AccountRole.ADMIN, service(repository, FakeStorage()))
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/menu-items",
            data={
                "name": "Frango",
                "size_options": ["P"],
                "size_prices": prices,
            },
        )
    assert response.status_code == 422, response.text
    assert not repository.items


def test_api_requires_every_enabled_size_when_no_base_price():
    app = app_for(AccountRole.ADMIN, service(FakeMenuRepository(), FakeStorage()))
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/menu-items",
            data={
                "name": "Frango",
                "size_options": ["P", "M"],
                "size_prices": '{"P":"12"}',
            },
        )
    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("method", [PaymentMethod.PIX, PaymentMethod.PAY_ON_DELIVERY])
async def test_order_totals_use_size_prices_and_keep_historical_snapshot(method):
    company, schedule = company_and_schedule()
    dish = MenuItem(
        uuid4(),
        "Frango",
        None,
        ["P", "M", "G"],
        Decimal("18.00"),
        size_prices={"P": Decimal("12.99"), "G": Decimal("23.90")},
    )
    repository = FakeOrderRepository()
    use_case = CreateOrder(
        repository,
        FakeCompanyRepository(company),
        OrderMenuRepository(menu(dish)),
        FakeSettingsRepository(),
    )
    order = await use_case.execute(
        command(
            company.id,
            schedule.id,
            [
                RequestedOrderItem(dish.id, "P", 2),
                RequestedOrderItem(dish.id, "M", 1),
                RequestedOrderItem(dish.id, "G", 1),
            ],
            payment_method=method,
        ),
        NOW,
        "America/Sao_Paulo",
    )
    assert [item.unit_price for item in order.items] == [
        Decimal("12.99"),
        Decimal("18.00"),
        Decimal("23.90"),
    ]
    assert order.total_price == Decimal("67.88")
    dish.size_prices["P"] = Decimal("99.00")
    assert order.items[0].unit_price == Decimal("12.99")
    assert order.total_price == Decimal("67.88")
    if method is PaymentMethod.PIX:
        payments, _, _, gateway = payment_service(order)
        checkout = await payments.pix_checkout(order.id, order.company_id, NOW)
        assert checkout.amount_cents == 6788
        assert gateway.created == [(order.id, 6788, order.cutoff_at)]


def test_legacy_and_zero_prices():
    dish = MenuItem(uuid4(), "Frango", None, ["P", "M"], Decimal("18"))
    assert dish.price_for_size("P") == Decimal("18")
    assert dish.price_for_size("G") is None
    dish.size_prices["P"] = Decimal("0")
    assert dish.price_for_size("P") == Decimal("0")
