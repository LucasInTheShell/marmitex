from dataclasses import dataclass
from datetime import datetime, time
from uuid import UUID


@dataclass(frozen=True, slots=True)
class MealScheduleDraft:
    label: str
    meal_time: time
    weekdays: list[int]
    sort_order: int = 0


@dataclass(frozen=True, slots=True)
class MealSchedule:
    id: UUID
    company_id: UUID
    label: str
    meal_time: time
    weekdays: list[int]
    active: bool
    sort_order: int


@dataclass(frozen=True, slots=True)
class Company:
    id: UUID
    name: str
    active: bool
    created_at: datetime
    access_email: str
    meal_schedules: list[MealSchedule]

