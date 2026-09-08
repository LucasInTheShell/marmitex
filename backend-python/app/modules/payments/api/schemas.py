from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.modules.orders.api.schemas import OrderResponse
from app.modules.orders.domain.entities import PaymentStatus


class PixCheckoutResponse(BaseModel):
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


class PaymentMethodChangeResponse(BaseModel):
    order: OrderResponse
