from datetime import date, datetime, time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.orders.domain.entities import (
    PaymentMethod,
    PaymentStatus,
    ProductionStatus,
)

SizeOption = Literal["P", "M", "G"]


class OrderItemCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    menu_item_id: UUID
    size: SizeOption
    quantity: int = Field(ge=1, le=10)
    notes: str | None = Field(default=None, max_length=300)


class OrderCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    date: date
    meal_schedule_id: UUID
    employee_name: str = Field(min_length=1, max_length=160)
    employee_phone: str = Field(min_length=10, max_length=24)
    employee_department: str = Field(min_length=1, max_length=120)
    employee_cpf: str = Field(min_length=11, max_length=18)
    employee_internal_id: str | None = Field(default=None, max_length=50)
    items: list[OrderItemCreate] = Field(min_length=1, max_length=10)
    payment_method: PaymentMethod = PaymentMethod.PAY_ON_DELIVERY


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    menu_item_id: UUID
    item_name: str
    item_description: str | None
    size: SizeOption
    quantity: int
    unit_price: float
    subtotal: float
    notes: str | None


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
    payment_method: PaymentMethod | None
    payment_status: PaymentStatus
    total_price: float
    created_at: datetime
    updated_at: datetime
    cancelled_at: datetime | None
    cancellation_reason: str | None
    items: list[OrderItemResponse]


class KitchenOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_number: int
    company_id: UUID
    company_name: str
    date: date
    meal_schedule_id: UUID | None
    meal_schedule_label: str | None
    scheduled_for: datetime | None
    employee_name: str
    employee_department: str
    employee_internal_id: str | None
    production_status: ProductionStatus
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemResponse]


class ProductionSizeSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    size: SizeOption
    quantity: int


class ProductionItemSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    menu_item_id: UUID
    item_name: str
    total_quantity: int
    sizes: list[ProductionSizeSummaryResponse]


class MealTimeProductionSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scheduled_for: datetime | None
    meal_time: time | None
    schedule_ids: list[UUID]
    schedule_labels: list[str]
    total_orders: int
    total_meals: int
    items: list[ProductionItemSummaryResponse]


class CompanyMealTimeProductionSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scheduled_for: datetime | None
    meal_time: time | None
    total_orders: int
    total_meals: int


class CompanyProductionSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    company_id: UUID
    company_name: str
    total_orders: int
    total_meals: int
    meal_times: list[CompanyMealTimeProductionSummaryResponse]
    items: list[ProductionItemSummaryResponse]


class DailyProductionSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date
    total_orders: int
    total_meals: int
    meal_times: list[MealTimeProductionSummaryResponse]
    companies: list[CompanyProductionSummaryResponse]


class OrderCancellationRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    reason: str | None = Field(default=None, max_length=300)


class ProductionStatusUpdateRequest(BaseModel):
    production_status: Literal["printed", "separated", "delivered"]
