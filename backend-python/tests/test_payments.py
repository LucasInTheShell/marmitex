from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.modules.companies.domain.entities import Company
from app.modules.orders.domain.entities import (
    Order,
    PaymentMethod,
    PaymentStatus,
    ProductionStatus,
)
from app.modules.payments.application.services import PaymentApplicationService
from app.modules.payments.domain.entities import (
    OrderPayment,
    PaymentEvent,
    PaymentPayer,
    PixPayment,
    ProviderPaymentSnapshot,
)
from app.modules.payments.domain.exceptions import (
    PaymentMethodChangeNotAllowedError,
    PaymentReconciliationError,
)

NOW = datetime.fromisoformat("2026-08-31T09:00:00-03:00")
CUTOFF = datetime.fromisoformat("2026-08-31T11:30:00-03:00")


def pix_order() -> Order:
    return Order(
        id=uuid4(),
        order_number=18,
        company_id=uuid4(),
        company_name="Empresa Teste",
        date=date(2026, 8, 31),
        meal_schedule_id=uuid4(),
        meal_schedule_label="Almoço",
        scheduled_for=datetime.fromisoformat("2026-08-31T13:00:00-03:00"),
        cutoff_at=CUTOFF,
        employee_name="Maria da Silva",
        employee_phone="11999998888",
        employee_department="Financeiro",
        employee_cpf="12345678901",
        employee_internal_id=None,
        production_status=ProductionStatus.PENDING,
        total_price=Decimal("24.90"),
        idempotency_key=None,
        request_fingerprint=None,
        created_at=NOW,
        updated_at=NOW,
        cancelled_at=None,
        cancellation_reason=None,
        items=[],
        payment_method=PaymentMethod.PIX,
        payment_status=PaymentStatus.PENDING,
    )


class FakeOrderRepository:
    def __init__(self, order: Order) -> None:
        self.order = order

    async def by_id(self, order_id: UUID, *, for_update: bool = False) -> Order | None:
        return self.order if self.order.id == order_id else None


class FakeCompanyRepository:
    def __init__(self, order: Order) -> None:
        self.company = Company(
            id=order.company_id,
            name=order.company_name,
            active=True,
            created_at=NOW,
            access_email="financeiro@empresa.test",
            meal_schedules=[],
        )

    async def by_id(self, company_id: UUID) -> Company | None:
        return self.company if company_id == self.company.id else None


class FakePaymentRepository:
    async def expire_unfunded(self, order_id: UUID, now: datetime) -> None:
        self.orders.order = replace(self.orders.order, payment_status=PaymentStatus.EXPIRED)

    def __init__(self, orders: FakeOrderRepository) -> None:
        self.orders = orders
        self.payment: OrderPayment | None = None
        self.applied: list[PaymentStatus] = []
        self.provider_customer_id: str | None = None

    async def by_order_id(self, order_id: UUID) -> OrderPayment | None:
        return self.payment if self.payment and self.payment.order_id == order_id else None

    async def by_provider_payment_id(
        self, provider: str, provider_payment_id: str
    ) -> OrderPayment | None:
        if (
            self.payment
            and self.payment.provider == provider
            and self.payment.provider_payment_id == provider_payment_id
        ):
            return self.payment
        return None

    async def customer_id(self, provider: str, company_id: UUID, employee_cpf: str) -> str | None:
        return self.provider_customer_id

    async def save_customer_id(
        self,
        provider: str,
        company_id: UUID,
        employee_cpf: str,
        provider_customer_id: str,
    ) -> str:
        self.provider_customer_id = provider_customer_id
        return provider_customer_id

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
        self.payment = OrderPayment(
            id=uuid4(),
            order_id=order_id,
            provider=provider,
            provider_payment_id=provider_payment_id,
            provider_status=provider_status,
            amount_cents=amount_cents,
            currency=currency,
            requested_expires_at=requested_expires_at,
            paid_at=None,
            failed_at=None,
            cancelled_at=None,
            created_at=NOW,
            updated_at=NOW,
        )
        return self.payment

    async def apply_event(self, event: PaymentEvent, payment_status: PaymentStatus) -> bool:
        self.applied.append(payment_status)
        self.orders.order = replace(self.orders.order, payment_status=payment_status)
        return True

    async def switch_order_to_delivery(self, order_id: UUID, changed_at: datetime) -> None:
        self.orders.order = replace(
            self.orders.order,
            payment_method=PaymentMethod.PAY_ON_DELIVERY,
            payment_status=PaymentStatus.NOT_APPLICABLE,
            updated_at=changed_at,
        )

    async def cancel_pix(self, order_id: UUID, changed_at: datetime) -> None:
        self.orders.order = replace(
            self.orders.order,
            payment_status=PaymentStatus.CANCELLED,
            updated_at=changed_at,
        )


class FakePaymentGateway:
    provider = "asaas"

    async def find_payment(self, order_id: UUID) -> ProviderPaymentSnapshot | None:
        if self.order_id == order_id:
            return await self.retrieve_payment("pay_test_123")
        return None

    def __init__(self) -> None:
        self.created: list[tuple[UUID, int, datetime]] = []
        self.cancelled: list[str] = []
        self.payers: list[PaymentPayer] = []
        self.order_id: UUID | None = None
        self.status = "PENDING"
        self.deleted = False
        self.has_refunds = False

    @property
    def configured(self) -> bool:
        return True

    async def get_or_create_customer(self, payer: PaymentPayer) -> str:
        self.payers.append(payer)
        return "cus_test_123"

    async def create_pix_payment(
        self,
        *,
        order_id: UUID,
        customer_id: str,
        amount_cents: int,
        expires_at: datetime,
        description: str,
    ) -> PixPayment:
        self.created.append((order_id, amount_cents, expires_at))
        self.order_id = order_id
        return PixPayment("pay_test_123", "PENDING", "base64-qr", "pix-copy-paste")

    async def retrieve_pix_payment(self, provider_payment_id: str) -> PixPayment:
        return PixPayment(provider_payment_id, "PENDING", "base64-qr", "pix-copy-paste")

    async def retrieve_payment(self, provider_payment_id: str) -> ProviderPaymentSnapshot:
        return ProviderPaymentSnapshot(
            provider_payment_id=provider_payment_id,
            provider_status=self.status,
            amount_cents=2490,
            currency="brl",
            external_reference=str(self.order_id),
            billing_type="PIX",
            deleted=self.deleted,
            has_refunds=self.has_refunds,
        )

    async def cancel_payment(self, provider_payment_id: str) -> None:
        self.cancelled.append(provider_payment_id)
        self.deleted = True


def service(order: Order | None = None):
    orders = FakeOrderRepository(order or pix_order())
    payments = FakePaymentRepository(orders)
    gateway = FakePaymentGateway()
    app = PaymentApplicationService(
        orders,  # type: ignore[arg-type]
        FakeCompanyRepository(orders.order),  # type: ignore[arg-type]
        payments,  # type: ignore[arg-type]
        gateway,  # type: ignore[arg-type]
    )
    return app, orders, payments, gateway


@pytest.mark.asyncio
async def test_pix_checkout_uses_server_total_and_company_email() -> None:
    app, orders, payments, gateway = service()

    checkout = await app.pix_checkout(
        orders.order.id,
        orders.order.company_id,
        NOW,
        employee_cpf=orders.order.employee_cpf,
    )

    assert gateway.created == [(orders.order.id, 2490, CUTOFF)]
    assert gateway.payers[0].email == "financeiro@empresa.test"
    assert payments.payment is not None
    assert checkout.amount_cents == 2490
    assert checkout.billing_email == "financeiro@empresa.test"
    assert checkout.billing_tax_id == "12345678901"
    assert checkout.provider == "asaas"
    assert checkout.qr_code_base64 == "base64-qr"
    assert checkout.pix_copy_paste == "pix-copy-paste"


@pytest.mark.asyncio
async def test_pending_pix_can_change_to_delivery_before_cutoff() -> None:
    app, orders, payments, gateway = service()
    await app.pix_checkout(orders.order.id, orders.order.company_id, NOW)

    updated = await app.switch_to_delivery(orders.order.id, orders.order.company_id, NOW)

    assert gateway.cancelled == ["pay_test_123"]
    assert updated.payment_method is PaymentMethod.PAY_ON_DELIVERY
    assert updated.payment_status is PaymentStatus.NOT_APPLICABLE


@pytest.mark.asyncio
async def test_paid_pix_cannot_change_to_delivery() -> None:
    order = replace(pix_order(), payment_status=PaymentStatus.PAID)
    app, orders, _, _ = service(order)

    with pytest.raises(PaymentMethodChangeNotAllowedError):
        await app.switch_to_delivery(orders.order.id, orders.order.company_id, NOW)


@pytest.mark.asyncio
async def test_webhook_reconciles_amount_currency_and_order() -> None:
    app, orders, payments, gateway = service()
    gateway.status = "RECEIVED"
    await app.pix_checkout(orders.order.id, orders.order.company_id, NOW)
    event = PaymentEvent(
        provider="asaas",
        id="evt_123",
        type="PAYMENT_RECEIVED",
        provider_payment_id="pay_test_123",
        provider_status="RECEIVED",
        amount_cents=2490,
        currency="brl",
        external_reference=str(orders.order.id),
        occurred_at=NOW,
    )

    assert await app.process_payment_event(event, NOW) is True
    assert payments.applied == [PaymentStatus.PAID]

    with pytest.raises(PaymentReconciliationError):
        await app.process_payment_event(replace(event, id="evt_wrong", amount_cents=1), NOW)
