from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.orders.api.schemas import OrderItemCreate
from app.modules.orders.domain.entities import PaymentMethod


class EmployeeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    company_name: str
    name: str
    cpf: str
    phone: str
    department: str
    internal_id: str | None
    active: bool
    created_at: datetime
    updated_at: datetime


class EmployeePublicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    company_name: str
    name: str
    department: str
    internal_id: str | None


class EmployeeCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    company_id: UUID | None = None
    name: str = Field(min_length=1, max_length=160)
    cpf: str = Field(min_length=11, max_length=18)
    phone: str = Field(min_length=10, max_length=24)
    department: str = Field(min_length=1, max_length=120)
    internal_id: str | None = Field(default=None, max_length=50)


class EmployeeUpdateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=160)
    phone: str | None = Field(default=None, min_length=10, max_length=24)
    department: str | None = Field(default=None, min_length=1, max_length=120)
    internal_id: str | None = Field(default=None, max_length=50)
    active: bool | None = None

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError("Informe ao menos um campo para atualizar.")
        return self


class EmployeeAccessRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    cpf: str = Field(min_length=11, max_length=18)


class EmployeeAccessResponse(BaseModel):
    token: str
    expires_at: datetime
    employee: EmployeePublicResponse


class EmployeeOrderCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    date: date
    meal_schedule_id: UUID
    items: list[OrderItemCreate] = Field(min_length=1, max_length=10)
    payment_method: PaymentMethod = PaymentMethod.PAY_ON_DELIVERY
