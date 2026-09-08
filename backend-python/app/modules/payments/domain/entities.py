from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.orders.domain.entities import PaymentStatus


@dataclass(frozen=True, slots=True)
class OrderPayment:
    id: UUID
    order_id: UUID
    provider: str
    provider_payment_id: str
    provider_status: str
    amount_cents: int
    currency: str
    requested_expires_at: datetime
    paid_at: datetime | None
    failed_at: datetime | None
    cancelled_at: datetime | None
    created_at: datetime
    updated_at: datetime
    confirmed_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class PaymentPayer:
    external_reference: str
    name: str
    tax_id: str
    email: str
    mobile_phone: str


@dataclass(frozen=True, slots=True)
class PixPayment:
    provider_payment_id: str
    provider_status: str
    qr_code_base64: str
    copy_paste: str


@dataclass(frozen=True, slots=True)
class ProviderPaymentSnapshot:
    provider_payment_id: str
    provider_status: str
    amount_cents: int
    currency: str
    external_reference: str | None
    billing_type: str
    deleted: bool = False
    has_refunds: bool = False


@dataclass(frozen=True, slots=True)
class PixCheckout:
    order_id: UUID
    payment_status: PaymentStatus
    provider: str
    provider_payment_id: str
    qr_code_base64: str
    pix_copy_paste: str
    billing_name: str
    billing_email: str
    billing_tax_id: str
    amount_cents: int
    currency: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class PaymentEvent:
    provider: str
    id: str
    type: str
    provider_payment_id: str
    provider_status: str
    amount_cents: int
    currency: str
    external_reference: str | None
    occurred_at: datetime
