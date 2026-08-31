import pytest
from pydantic import ValidationError

from app.modules.companies.api.schemas import CompanyCreate, MealScheduleCreate


def test_company_accepts_multiple_meal_schedules() -> None:
    company = CompanyCreate(
        name="Empresa",
        email="contato@empresa.com.br",
        password="safe-password",
        meal_schedules=[
            MealScheduleCreate(
                label="Primeiro turno", meal_time="11:30", weekdays=[1, 2, 3, 4, 5]
            ),
            MealScheduleCreate(
                label="Segundo turno", meal_time="13:00", weekdays=[1, 2, 3, 4, 5]
            ),
        ],
    )

    assert len(company.meal_schedules) == 2
    assert company.meal_schedules[1].meal_time.hour == 13


def test_company_requires_at_least_one_meal_schedule() -> None:
    with pytest.raises(ValidationError):
        CompanyCreate(
            name="Empresa",
            email="contato@empresa.com.br",
            password="safe-password",
            meal_schedules=[],
        )


def test_schedule_normalizes_and_validates_weekdays() -> None:
    schedule = MealScheduleCreate(
        label="  Almoço  ", meal_time="12:00", weekdays=[5, 1, 1, 3]
    )

    assert schedule.label == "Almoço"
    assert schedule.weekdays == [1, 3, 5]

    with pytest.raises(ValidationError):
        MealScheduleCreate(label="Inválido", meal_time="12:00", weekdays=[0, 8])


def test_company_rejects_duplicate_schedule_labels() -> None:
    with pytest.raises(ValidationError):
        CompanyCreate(
            name="Empresa",
            email="contato@empresa.com.br",
            password="safe-password",
            meal_schedules=[
                MealScheduleCreate(label="Almoço", meal_time="12:00"),
                MealScheduleCreate(label=" almoço ", meal_time="13:00"),
            ],
        )
