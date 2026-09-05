from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class ProductionStatus(StrEnum):
    PENDING = "pending"
    PRINTED = "printed"
    SEPARATED = "separated"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class PaymentMethod(StrEnum):
    PAY_ON_DELIVERY = "pay_on_delivery"
    PIX = "pix"


class PaymentStatus(StrEnum):
    NOT_APPLICABLE = "not_applicable"
    PENDING = "pending"
    PROCESSING = "processing"
    PAID = "paid"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    REVIEW_REQUIRED = "review_required"


@dataclass(frozen=True, slots=True)
class OrderItemDraft:
    menu_item_id: UUID
    item_name: str
    item_description: str | None
    size: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal
    notes: str | None


@dataclass(frozen=True, slots=True)
class OrderDraft:
    company_id: UUID
    date: date
    meal_schedule_id: UUID
    meal_schedule_label: str
    scheduled_for: datetime
    cutoff_at: datetime
    employee_name: str
    employee_phone: str
    employee_department: str
    employee_cpf: str
    employee_internal_id: str | None
    total_price: Decimal
    idempotency_key: str | None
    request_fingerprint: str | None
    items: list[OrderItemDraft]
    payment_method: PaymentMethod = PaymentMethod.PAY_ON_DELIVERY
    payment_status: PaymentStatus = PaymentStatus.NOT_APPLICABLE


@dataclass(frozen=True, slots=True)
class OrderItem:
    id: UUID
    menu_item_id: UUID
    item_name: str
    item_description: str | None
    size: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal
    notes: str | None


@dataclass(frozen=True, slots=True)
class Order:
    id: UUID
    order_number: int
    company_id: UUID
    company_name: str
    date: date
    meal_schedule_id: UUID | None
    meal_schedule_label: str | None
    scheduled_for: datetime | None
    cutoff_at: datetime | None
    employee_name: str
    employee_phone: str
    employee_department: str
    employee_cpf: str
    employee_internal_id: str | None
    production_status: ProductionStatus
    total_price: Decimal
    idempotency_key: str | None
    request_fingerprint: str | None
    created_at: datetime
    updated_at: datetime
    cancelled_at: datetime | None
    cancellation_reason: str | None
    items: list[OrderItem]
    payment_method: PaymentMethod | None = None
    payment_status: PaymentStatus = PaymentStatus.NOT_APPLICABLE


@dataclass(frozen=True, slots=True)
class ProductionSizeSummary:
    size: str
    quantity: int


@dataclass(frozen=True, slots=True)
class ProductionItemSummary:
    menu_item_id: UUID
    item_name: str
    total_quantity: int
    sizes: list[ProductionSizeSummary]


@dataclass(frozen=True, slots=True)
class MealTimeProductionSummary:
    scheduled_for: datetime | None
    meal_time: time | None
    schedule_ids: list[UUID]
    schedule_labels: list[str]
    total_orders: int
    total_meals: int
    items: list[ProductionItemSummary]


@dataclass(frozen=True, slots=True)
class CompanyMealTimeProductionSummary:
    scheduled_for: datetime | None
    meal_time: time | None
    total_orders: int
    total_meals: int


@dataclass(frozen=True, slots=True)
class CompanyProductionSummary:
    company_id: UUID
    company_name: str
    total_orders: int
    total_meals: int
    meal_times: list[CompanyMealTimeProductionSummary]
    items: list[ProductionItemSummary]


@dataclass(frozen=True, slots=True)
class DailyProductionSummary:
    date: date
    total_orders: int
    total_meals: int
    meal_times: list[MealTimeProductionSummary]
    companies: list[CompanyProductionSummary]
