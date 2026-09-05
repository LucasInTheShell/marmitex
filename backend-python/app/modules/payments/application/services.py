from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from app.modules.companies.domain.repositories import CompanyRepository
from app.modules.orders.domain.entities import (
    Order,
    PaymentMethod,
    PaymentStatus,
    ProductionStatus,
)
from app.modules.orders.domain.exceptions import OrderNotFoundError
from app.modules.orders.domain.repositories import OrderRepository
from app.modules.payments.domain.entities import (
    OrderPayment,
    PaymentEvent,
    PaymentPayer,
    PixCheckout,
    ProviderPaymentSnapshot,
)
from app.modules.payments.domain.exceptions import (
    PaymentMethodChangeNotAllowedError,
    PaymentNotFoundError,
    PaymentReconciliationError,
    PixUnavailableError,
)
from app.modules.payments.domain.repositories import PaymentGateway, PaymentRepository

MIN_PIX_AMOUNT_CENTS = 50
MIN_PIX_LIFETIME = timedelta(seconds=10)
MAX_PIX_LIFETIME = timedelta(days=14)


class PaymentApplicationService:
    def __init__(
        self,
        orders: OrderRepository,
        companies: CompanyRepository,
        payments: PaymentRepository,
        gateway: PaymentGateway,
    ) -> None:
        self.orders = orders
        self.companies = companies
        self.payments = payments
        self.gateway = gateway

    async def pix_checkout(
        self,
        order_id: UUID,
        company_id: UUID,
        now: datetime,
        employee_cpf: str | None = None,
    ) -> PixCheckout:
        order = await self._authorized_order(order_id, company_id, employee_cpf)
        if not self.gateway.configured:
            raise PixUnavailableError("O Pix ainda não foi configurado.")
        self._validate_pix_order(order, now)
        company = await self.companies.by_id(order.company_id)
        if company is None or not company.access_email:
            raise PixUnavailableError("A empresa não possui e-mail de cobrança.")

        payment = await self.payments.by_order_id(order.id)
        if payment is None:
            amount_cents = self._amount_cents(order.total_price)
            provider_customer_id = await self.payments.customer_id(
                self.gateway.provider, order.company_id, order.employee_cpf
            )
            if provider_customer_id is None:
                provider_customer_id = await self.gateway.get_or_create_customer(
                    PaymentPayer(
                        external_reference=self._payer_reference(
                            order.company_id, order.employee_cpf
                        ),
                        name=order.employee_name,
                        tax_id=order.employee_cpf,
                        email=company.access_email,
                        mobile_phone=order.employee_phone,
                    )
                )
                provider_customer_id = await self.payments.save_customer_id(
                    self.gateway.provider,
                    order.company_id,
                    order.employee_cpf,
                    provider_customer_id,
                )
            pix_payment = await self.gateway.create_pix_payment(
                order_id=order.id,
                customer_id=provider_customer_id,
                amount_cents=amount_cents,
                expires_at=order.cutoff_at,  # type: ignore[arg-type]
                description=f"Pedido #{order.order_number} - {company.name}"[:500],
            )
            payment = await self.payments.create(
                order.id,
                self.gateway.provider,
                pix_payment.provider_payment_id,
                pix_payment.provider_status,
                amount_cents,
                "brl",
                order.cutoff_at,  # type: ignore[arg-type]
            )
        else:
            if payment.provider != self.gateway.provider:
                raise PaymentReconciliationError()
            pix_payment = await self.gateway.retrieve_pix_payment(payment.provider_payment_id)

        if pix_payment.provider_status != "PENDING":
            snapshot = await self.gateway.retrieve_payment(payment.provider_payment_id)
            self._validate_snapshot(payment, snapshot)
            event = PaymentEvent(
                payment.provider,
                f"checkout:{uuid4()}",
                "RECONCILIATION",
                payment.provider_payment_id,
                snapshot.provider_status,
                snapshot.amount_cents,
                snapshot.currency,
                snapshot.external_reference,
                now,
            )
            await self._apply_snapshot(order, payment, snapshot, event)
            updated = await self.orders.by_id(order.id)
            if updated is not None:
                order = updated
        return PixCheckout(
            order_id=order.id,
            payment_status=order.payment_status,
            provider=self.gateway.provider,
            provider_payment_id=pix_payment.provider_payment_id,
            qr_code_base64=pix_payment.qr_code_base64,
            pix_copy_paste=pix_payment.copy_paste,
            billing_name=order.employee_name,
            billing_email=company.access_email,
            billing_tax_id=order.employee_cpf,
            amount_cents=payment.amount_cents,
            currency=payment.currency,
            expires_at=payment.requested_expires_at,
        )

    async def switch_to_delivery(
        self,
        order_id: UUID,
        company_id: UUID,
        now: datetime,
        employee_cpf: str | None = None,
    ) -> Order:
        order = await self._authorized_order(order_id, company_id, employee_cpf)
        if (
            order.payment_method is not PaymentMethod.PIX
            or order.payment_status
            in {
                PaymentStatus.PAID,
                PaymentStatus.PROCESSING,
                PaymentStatus.REFUNDED,
                PaymentStatus.REVIEW_REQUIRED,
            }
            or order.production_status is not ProductionStatus.PENDING
            or order.cutoff_at is None
            or now >= order.cutoff_at
        ):
            raise PaymentMethodChangeNotAllowedError()
        payment = await self.payments.by_order_id(order.id)
        if payment is not None and payment.cancelled_at is None:
            self._ensure_current_provider(payment.provider)
            await self._assert_cancellable(payment)
            await self.gateway.cancel_payment(payment.provider_payment_id)
        await self.payments.switch_order_to_delivery(order.id, now)
        updated = await self.orders.by_id(order.id)
        if updated is None:
            raise OrderNotFoundError()
        return updated

    async def cancel_pending_for_order(self, order_id: UUID, now: datetime) -> None:
        order = await self.orders.by_id(order_id, for_update=True)
        if order is None:
            raise OrderNotFoundError()
        if order.payment_method is not PaymentMethod.PIX:
            return
        if order.payment_status in {
            PaymentStatus.PAID,
            PaymentStatus.PROCESSING,
            PaymentStatus.REFUNDED,
            PaymentStatus.REVIEW_REQUIRED,
        }:
            raise PaymentMethodChangeNotAllowedError()
        payment = await self.payments.by_order_id(order_id)
        if payment is not None and payment.cancelled_at is None:
            self._ensure_current_provider(payment.provider)
            await self._assert_cancellable(payment)
            await self.gateway.cancel_payment(payment.provider_payment_id)
        await self.payments.cancel_pix(order_id, now)

    async def process_payment_event(self, event: PaymentEvent, now: datetime | None = None) -> bool:
        if event.provider != self.gateway.provider:
            return False
        payment = await self.payments.by_provider_payment_id(
            event.provider, event.provider_payment_id
        )
        if payment is None:
            # Recover a charge created remotely before a timeout/local rollback.
            snapshot = await self.gateway.retrieve_payment(event.provider_payment_id)
            try:
                order_id = UUID(snapshot.external_reference or "")
            except ValueError as error:
                raise PaymentNotFoundError() from error
            order = await self.orders.by_id(order_id, for_update=True)
            if order is None or order.cutoff_at is None:
                raise PaymentNotFoundError()
            payment = await self.payments.by_order_id(order.id)
            if payment is None:
                if (
                    snapshot.billing_type != "PIX"
                    or snapshot.currency != "brl"
                    or snapshot.amount_cents != self._amount_cents(order.total_price)
                ):
                    raise PaymentReconciliationError()
                payment = await self.payments.create(
                    order.id,
                    event.provider,
                    snapshot.provider_payment_id,
                    snapshot.provider_status,
                    snapshot.amount_cents,
                    snapshot.currency,
                    order.cutoff_at,
                )
        order = await self.orders.by_id(payment.order_id, for_update=True)
        if order is None:
            raise PaymentNotFoundError()
        payment = await self.payments.by_order_id(order.id)
        assert payment is not None
        if (
            event.external_reference != str(payment.order_id)
            or event.amount_cents != payment.amount_cents
            or event.currency != payment.currency
        ):
            raise PaymentReconciliationError()
        snapshot = await self.gateway.retrieve_payment(event.provider_payment_id)
        self._validate_snapshot(payment, snapshot)
        return await self._apply_snapshot(
            order, payment, snapshot, replace(event, occurred_at=now or datetime.now(UTC))
        )

    async def reconcile_order(self, order_id: UUID, now: datetime) -> None:
        order = await self.orders.by_id(order_id, for_update=True)
        payment = await self.payments.by_order_id(order_id)
        if order is None:
            return
        if payment is None:
            if order.payment_method is not PaymentMethod.PIX or order.cutoff_at is None:
                return
            snapshot = await self.gateway.find_payment(order.id)
            if snapshot is None:
                if now >= order.cutoff_at:
                    await self.payments.expire_unfunded(order.id, now)
                return
            if (
                snapshot.external_reference != str(order.id)
                or snapshot.billing_type != "PIX"
                or snapshot.currency != "brl"
                or snapshot.amount_cents != self._amount_cents(order.total_price)
            ):
                raise PaymentReconciliationError()
            payment = await self.payments.create(
                order.id,
                self.gateway.provider,
                snapshot.provider_payment_id,
                snapshot.provider_status,
                snapshot.amount_cents,
                snapshot.currency,
                order.cutoff_at,
            )
        if payment.provider != self.gateway.provider:
            return
        snapshot = await self.gateway.retrieve_payment(payment.provider_payment_id)
        self._validate_snapshot(payment, snapshot)
        if (
            now >= payment.requested_expires_at
            and not snapshot.deleted
            and snapshot.provider_status in {"PENDING", "OVERDUE"}
            and not snapshot.has_refunds
        ):
            await self.gateway.cancel_payment(payment.provider_payment_id)
            # A fresh read catches a payment racing the removal.
            snapshot = await self.gateway.retrieve_payment(payment.provider_payment_id)
            self._validate_snapshot(payment, snapshot)
        event = PaymentEvent(
            provider=payment.provider,
            id=f"reconcile:{uuid4()}",
            type="RECONCILIATION",
            provider_payment_id=payment.provider_payment_id,
            provider_status=snapshot.provider_status,
            amount_cents=snapshot.amount_cents,
            currency=snapshot.currency,
            external_reference=snapshot.external_reference,
            occurred_at=now,
        )
        await self._apply_snapshot(order, payment, snapshot, event)

    async def _assert_cancellable(self, payment: OrderPayment) -> None:
        snapshot = await self.gateway.retrieve_payment(payment.provider_payment_id)
        self._validate_snapshot(payment, snapshot)
        if snapshot.has_refunds or snapshot.provider_status not in {"PENDING", "OVERDUE"}:
            raise PaymentMethodChangeNotAllowedError()

    @staticmethod
    def _validate_snapshot(payment: OrderPayment, snapshot: ProviderPaymentSnapshot) -> None:
        if (
            snapshot.provider_payment_id != payment.provider_payment_id
            or snapshot.external_reference != str(payment.order_id)
            or snapshot.currency != payment.currency
            or snapshot.amount_cents != payment.amount_cents
            or snapshot.billing_type != "PIX"
        ):
            raise PaymentReconciliationError()

    async def _apply_snapshot(
        self,
        order: Order,
        payment: OrderPayment,
        snapshot: ProviderPaymentSnapshot,
        event: PaymentEvent,
    ) -> bool:
        # Never infer settlement from the event name. Events can be delayed/reordered.
        statuses = {
            "PENDING": PaymentStatus.PENDING,
            "OVERDUE": PaymentStatus.EXPIRED,
            "CONFIRMED": PaymentStatus.PROCESSING,
            "RECEIVED": PaymentStatus.PAID,
            "REFUNDED": PaymentStatus.REFUNDED,
            "AWAITING_RISK_ANALYSIS": PaymentStatus.PROCESSING,
        }
        status = statuses.get(snapshot.provider_status, PaymentStatus.REVIEW_REQUIRED)
        if snapshot.deleted and snapshot.provider_status in {"PENDING", "OVERDUE"}:
            status = (
                PaymentStatus.EXPIRED
                if event.occurred_at >= payment.requested_expires_at
                else PaymentStatus.CANCELLED
            )
        elif snapshot.has_refunds and status is not PaymentStatus.REFUNDED:
            status = PaymentStatus.REVIEW_REQUIRED
        if status in {PaymentStatus.PAID, PaymentStatus.PROCESSING} and (
            order.payment_method is not PaymentMethod.PIX
            or order.production_status is ProductionStatus.CANCELLED
            or (
                event.occurred_at >= payment.requested_expires_at
                and payment.confirmed_at is None
                and payment.paid_at is None
            )
        ):
            status = PaymentStatus.REVIEW_REQUIRED
        normalized = replace(
            event,
            provider_status=("DELETED" if snapshot.deleted else snapshot.provider_status),
            amount_cents=snapshot.amount_cents,
            external_reference=snapshot.external_reference,
        )
        return await self.payments.apply_event(normalized, status)

    def _ensure_current_provider(self, provider: str) -> None:
        if provider != self.gateway.provider:
            raise PaymentReconciliationError()

    @staticmethod
    def _payer_reference(company_id: UUID, employee_cpf: str) -> str:
        return str(uuid5(NAMESPACE_URL, f"mavi:{company_id}:{employee_cpf}"))

    async def _authorized_order(
        self,
        order_id: UUID,
        company_id: UUID,
        employee_cpf: str | None,
    ) -> Order:
        # The request transaction holds this lock across the provider call and commit.
        order = await self.orders.by_id(order_id, for_update=True)
        if (
            order is None
            or order.company_id != company_id
            or (employee_cpf is not None and order.employee_cpf != employee_cpf)
        ):
            raise OrderNotFoundError()
        return order

    @staticmethod
    def _validate_pix_order(order: Order, now: datetime) -> None:
        if order.payment_method is not PaymentMethod.PIX:
            raise PixUnavailableError()
        if order.payment_status in {
            PaymentStatus.PAID,
            PaymentStatus.PROCESSING,
            PaymentStatus.CANCELLED,
            PaymentStatus.REFUNDED,
            PaymentStatus.REVIEW_REQUIRED,
        }:
            raise PixUnavailableError()
        if order.production_status is not ProductionStatus.PENDING:
            raise PixUnavailableError()
        if order.cutoff_at is None:
            raise PixUnavailableError()
        remaining = order.cutoff_at - now
        if remaining < MIN_PIX_LIFETIME or remaining > MAX_PIX_LIFETIME:
            raise PixUnavailableError("O prazo disponível para este Pix é inválido.")
        if PaymentApplicationService._amount_cents(order.total_price) < MIN_PIX_AMOUNT_CENTS:
            raise PixUnavailableError("O valor mínimo para pagamento via Pix é R$ 0,50.")

    @staticmethod
    def _amount_cents(amount: Decimal) -> int:
        return int(amount * 100)
