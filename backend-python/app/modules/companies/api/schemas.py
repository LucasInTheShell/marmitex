from datetime import datetime, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class MealScheduleCreate(BaseModel):
    label: str = Field(min_length=1, max_length=80)
    meal_time: time
    weekdays: list[int] = Field(
        default_factory=lambda: [1, 2, 3, 4, 5], min_length=1, max_length=7
    )
    sort_order: int = Field(default=0, ge=0, le=100)

    @field_validator("label")
    @classmethod
    def normalize_label(cls, value: str) -> str:
        label = value.strip()
        if not label:
            raise ValueError("O nome do horário é obrigatório.")
        return label

    @field_validator("weekdays")
    @classmethod
    def validate_weekdays(cls, value: list[int]) -> list[int]:
        if any(day < 1 or day > 7 for day in value):
            raise ValueError("Os dias da semana devem estar entre 1 e 7.")
        return sorted(set(value))


class MealScheduleUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=80)
    meal_time: time | None = None
    weekdays: list[int] | None = Field(default=None, min_length=1, max_length=7)
    active: bool | None = None
    sort_order: int | None = Field(default=None, ge=0, le=100)

    @field_validator("label")
    @classmethod
    def normalize_label(cls, value: str | None) -> str | None:
        if value is None:
            return None
        label = value.strip()
        if not label:
            raise ValueError("O nome do horário é obrigatório.")
        return label

    @field_validator("weekdays")
    @classmethod
    def validate_weekdays(cls, value: list[int] | None) -> list[int] | None:
        if value is None:
            return None
        if any(day < 1 or day > 7 for day in value):
            raise ValueError("Os dias da semana devem estar entre 1 e 7.")
        return sorted(set(value))

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError("Informe ao menos um campo para atualizar.")
        return self


class MealScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    label: str
    meal_time: time
    weekdays: list[int]
    active: bool
    sort_order: int


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)
    meal_schedules: list[MealScheduleCreate] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def validate_unique_schedule_labels(self):
        labels = [schedule.label.strip().casefold() for schedule in self.meal_schedules]
        if len(labels) != len(set(labels)):
            raise ValueError("Os nomes dos horários precisam ser diferentes.")
        return self


class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    active: bool
    created_at: datetime
    access_email: str
    meal_schedules: list[MealScheduleResponse]

