import json
from dataclasses import replace
from uuid import uuid4

import httpx
import pytest

from app.modules.orders.domain.entities import PaymentStatus
from app.modules.payments.domain.entities import PaymentEvent, PaymentPayer
from app.modules.payments.domain.exceptions import (
    InvalidPaymentWebhookError,
    PaymentMethodChangeNotAllowedError,
    PaymentProviderError,
)
from app.modules.payments.infrastructure.asaas_gateway import AsaasPaymentGateway
from tests.test_payments import CUTOFF, NOW, service

TOKEN = "test-webhook-token-with-at-least-32-characters"


def gateway(handler):
    return AsaasPaymentGateway("test-key", TOKEN, transport=httpx.MockTransport(handler))


async def test_customer_and_lean_charge_contract():
    requests = []
    order_id = uuid4()

    def handler(request):
        requests.append(request)
        assert request.headers["access_token"] == "test-key"
        assert request.headers["user-agent"] == "mavi-connect/0.1.0"
        if request.method == "GET":
            assert request.content == b""
            if request.url.path.endswith("pixQrCode"):
                return httpx.Response(200, json={"encodedImage": "qr", "payload": "pix-code"})
            return httpx.Response(200, json={"data": []})
        body = json.loads(request.content)
        if request.url.path == "/v3/customers":
            assert body["email"] == "empresa@example.test"
            assert body["notificationDisabled"] is True
            assert body["cpfCnpj"] == "12345678901"
            return httpx.Response(200, json={"id": "cus_test"})
        assert request.url.path == "/v3/lean/payments"
        assert body == {
            "customer": "cus_test",
            "billingType": "PIX",
            "value": 24.9,
            "dueDate": CUTOFF.date().isoformat(),
            "description": "Pedido teste",
            "externalReference": str(order_id),
        }
        return httpx.Response(200, json={"id": "pay_test", "status": "PENDING"})

    adapter = gateway(handler)
    customer = await adapter.get_or_create_customer(
        PaymentPayer(
            "ref",
            "Teste",
            "123.456.789-01",
            "empresa@example.test",
            "11999998888",
        )
    )
    pix = await adapter.create_pix_payment(
        order_id=order_id,
        customer_id=customer,
        amount_cents=2490,
        expires_at=CUTOFF,
        description="Pedido teste",
    )
    assert pix.copy_paste == "pix-code"
    assert len(requests) == 5


async def test_existing_charge_is_reused_without_post():
    def handler(request):
        assert request.method == "GET"
        if request.url.path.endswith("pixQrCode"):
            return httpx.Response(200, json={"encodedImage": "qr", "payload": "code"})
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "id": "pay_existing",
                        "value": 24.9,
                        "customer": "cus_test",
                        "billingType": "PIX",
                        "status": "PENDING",
                    }
                ]
            },
        )

    result = await gateway(handler).create_pix_payment(
        order_id=uuid4(),
        customer_id="cus_test",
        amount_cents=2490,
        expires_at=CUTOFF,
        description="Teste",
    )
    assert result.provider_payment_id == "pay_existing"


@pytest.mark.parametrize("token", [None, "wrong", "á" * 40])
def test_webhook_rejects_invalid_authentication(token):
    with pytest.raises(InvalidPaymentWebhookError):
        gateway(lambda request: None).parse_webhook(b"{}", token)


def test_webhook_normalizes_payload():
    body = {
        "id": "evt_test",
        "event": "PAYMENT_RECEIVED",
        "payment": {
            "id": "pay_test",
            "value": 24.9,
            "externalReference": str(uuid4()),
            "status": "RECEIVED",
        },
    }
    event = gateway(lambda request: None).parse_webhook(json.dumps(body).encode(), TOKEN)
    assert event.amount_cents == 2490
    assert event.provider == "asaas"


async def test_cannot_delete_received_charge():
    def handler(request):
        assert request.method == "GET"
        return httpx.Response(
            200, json={"id": "pay_test", "value": 24.9, "billingType": "PIX", "status": "RECEIVED"}
        )

    with pytest.raises(PaymentMethodChangeNotAllowedError):
        await gateway(handler).cancel_payment("pay_test")


async def test_delete_checks_ack_and_current_state():
    deleted = False

    def handler(request):
        nonlocal deleted
        if request.method == "DELETE":
            deleted = True
            return httpx.Response(200, json={"deleted": True, "id": "pay_test"})
        return httpx.Response(
            200,
            json={
                "id": "pay_test",
                "value": 24.9,
                "billingType": "PIX",
                "status": "PENDING",
                "deleted": deleted,
            },
        )

    await gateway(handler).cancel_payment("pay_test")
    assert deleted


@pytest.mark.parametrize("response", [{"id": "pay_test", "value": "NaN"}, {}])
async def test_malformed_provider_response_is_controlled(response):
    with pytest.raises(PaymentProviderError):
        await gateway(lambda request: httpx.Response(200, json=response)).retrieve_payment(
            "pay_test"
        )


def event_for(order):
    return PaymentEvent(
        "asaas",
        "evt_test",
        "PAYMENT_RECEIVED",
        "pay_test_123",
        "RECEIVED",
        2490,
        "brl",
        str(order.id),
        NOW,
    )


@pytest.mark.parametrize(
    "provider_status, expected",
    [
        ("PENDING", PaymentStatus.PENDING),
        ("CONFIRMED", PaymentStatus.PROCESSING),
        ("RECEIVED", PaymentStatus.PAID),
        ("REFUNDED", PaymentStatus.REFUNDED),
        ("UNKNOWN", PaymentStatus.REVIEW_REQUIRED),
    ],
)
async def test_event_name_never_overrides_provider_state(provider_status, expected):
    app, orders, payments, adapter = service()
    await app.pix_checkout(orders.order.id, orders.order.company_id, NOW)
    adapter.status = provider_status
    await app.process_payment_event(event_for(orders.order), NOW)
    assert payments.applied == [expected]


async def test_late_received_requires_review():
    app, orders, payments, adapter = service()
    await app.pix_checkout(orders.order.id, orders.order.company_id, NOW)
    adapter.status = "RECEIVED"
    await app.process_payment_event(event_for(orders.order), CUTOFF)
    assert payments.applied == [PaymentStatus.REVIEW_REQUIRED]


async def test_prior_confirmation_allows_delayed_settlement():
    app, orders, payments, adapter = service()
    await app.pix_checkout(orders.order.id, orders.order.company_id, NOW)
    payments.payment = replace(payments.payment, confirmed_at=NOW)
    adapter.status = "RECEIVED"
    await app.process_payment_event(event_for(orders.order), CUTOFF)
    assert payments.applied == [PaymentStatus.PAID]


async def test_cutoff_sweep_cancels_pending_charge():
    app, orders, payments, adapter = service()
    await app.pix_checkout(orders.order.id, orders.order.company_id, NOW)
    await app.reconcile_order(orders.order.id, CUTOFF)
    assert adapter.cancelled == ["pay_test_123"]
    assert payments.applied == [PaymentStatus.EXPIRED]


async def test_cutoff_sweep_does_not_delete_received_charge():
    app, orders, payments, adapter = service()
    await app.pix_checkout(orders.order.id, orders.order.company_id, NOW)
    adapter.status = "RECEIVED"
    await app.reconcile_order(orders.order.id, CUTOFF)
    assert not adapter.cancelled
    assert payments.applied == [PaymentStatus.REVIEW_REQUIRED]


async def test_webhook_recovers_charge_after_local_rollback():
    app, orders, payments, adapter = service()
    adapter.order_id = orders.order.id
    adapter.status = "RECEIVED"
    await app.process_payment_event(event_for(orders.order), NOW)
    assert payments.payment.provider_payment_id == "pay_test_123"
    assert payments.applied == [PaymentStatus.PAID]


async def test_partial_refund_requires_review():
    app, orders, payments, adapter = service()
    await app.pix_checkout(orders.order.id, orders.order.company_id, NOW)
    adapter.status = "RECEIVED"
    adapter.has_refunds = True
    await app.process_payment_event(event_for(orders.order), NOW)
    assert payments.applied == [PaymentStatus.REVIEW_REQUIRED]


async def test_cutoff_recovers_orphan_remote_charge_without_webhook():
    app, orders, payments, adapter = service()
    adapter.order_id = orders.order.id
    await app.reconcile_order(orders.order.id, CUTOFF)
    assert payments.payment is not None
    assert adapter.cancelled == ["pay_test_123"]
    assert payments.applied == [PaymentStatus.EXPIRED]


async def test_cutoff_expires_order_without_any_remote_charge():
    app, orders, _, _ = service()
    await app.reconcile_order(orders.order.id, CUTOFF)
    assert orders.order.payment_status is PaymentStatus.EXPIRED
