from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from uuid import UUID


class ProductionStatus(StrEnum):
    PENDING = "pending"
    PRINTED = "printed"
    SEPARATED = "separated"
    DELIVERED = "delivered"


@dataclass(frozen=True, slots=True)
class Order:
    id: UUID
    company_id: UUID
    date: date
    menu_item_id: UUID
    size: str
    employee_name: str
    employee_phone: str
    employee_department: str
    employee_cpf: str
    production_status: ProductionStatus
    created_at: datetime

