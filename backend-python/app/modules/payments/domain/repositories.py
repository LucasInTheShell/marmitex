from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.modules.orders.domain.entities import PaymentStatus
from app.modules.payments.domain.entities import (
    OrderPayment,
    PaymentEvent,
    PaymentPayer,
    PixPayment,
    ProviderPaymentSnapshot,
)


class PaymentRepository(Protocol):
    async def enqueue_event(self, event: PaymentEvent) -> None: ...

    async def complete_event(self, event: PaymentEvent) -> None: ...

    async def expire_unfunded(self, order_id: UUID, now: datetime) -> None: ...

    async def by_order_id(self, order_id: UUID) -> OrderPayment | None: ...

    async def by_provider_payment_id(
        self, provider: str, provider_payment_id: str
    ) -> OrderPayment | None: ...

    async def customer_id(
        self, provider: str, company_id: UUID, employee_cpf: str
    ) -> str | None: ...

    async def save_customer_id(
        self,
        provider: str,
        company_id: UUID,
        employee_cpf: str,
        provider_customer_id: str,
    ) -> str: ...

    async def create(
        self,
        order_id: UUID,
        provider: str,
        provider_payment_id: str,
        provider_status: str,
        amount_cents: int,
        currency: str,
        requested_expires_at: datetime,
    ) -> OrderPayment: ...

    async def apply_event(
        self,
        event: PaymentEvent,
        payment_status: PaymentStatus,
    ) -> bool: ...

    async def switch_order_to_delivery(self, order_id: UUID, changed_at: datetime) -> None: ...

    async def cancel_pix(self, order_id: UUID, changed_at: datetime) -> None: ...


class PaymentGateway(Protocol):
    provider: str

    async def find_payment(self, order_id: UUID) -> ProviderPaymentSnapshot | None: ...

    @property
    def configured(self) -> bool: ...

    async def get_or_create_customer(self, payer: PaymentPayer) -> str: ...

    async def create_pix_payment(
        self,
        *,
        order_id: UUID,
        customer_id: str,
        amount_cents: int,
        expires_at: datetime,
        description: str,
    ) -> PixPayment: ...

    async def retrieve_pix_payment(self, provider_payment_id: str) -> PixPayment: ...

    async def retrieve_payment(self, provider_payment_id: str) -> ProviderPaymentSnapshot: ...

    async def cancel_payment(self, provider_payment_id: str) -> None: ...

    def parse_webhook(self, payload: bytes, token: str | None) -> PaymentEvent: ...
