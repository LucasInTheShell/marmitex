from __future__ import annotations

from datetime import time
from uuid import UUID

from app.modules.companies.domain.entities import Company, MealSchedule, MealScheduleDraft
from app.modules.companies.domain.exceptions import (
    CompanyConflictError,
    CompanyNotFoundError,
    DuplicateCompanyEmailError,
    DuplicateMealScheduleError,
    MealScheduleConflictError,
    MealScheduleLimitError,
    MealScheduleNotFoundError,
)
from app.modules.companies.domain.repositories import CompanyRepository, PasswordHasher


class CompanyApplicationService:
    def __init__(
        self, repository: CompanyRepository, password_hasher: PasswordHasher
    ) -> None:
        self.repository = repository
        self.password_hasher = password_hasher

    async def list(self) -> list[Company]:
        return await self.repository.list()

    async def by_id(self, company_id: UUID) -> Company:
        company = await self.repository.by_id(company_id)
        if company is None:
            raise CompanyNotFoundError()
        return company

    async def create(
        self,
        name: str,
        email: str,
        password: str,
        meal_schedules: list[MealScheduleDraft],
    ) -> Company:
        try:
            return await self.repository.create(
                name,
                email.lower(),
                self.password_hasher.hash(password),
                meal_schedules,
            )
        except DuplicateCompanyEmailError as error:
            raise CompanyConflictError from error
        except DuplicateMealScheduleError as error:
            raise MealScheduleConflictError from error

    async def add_meal_schedule(
        self, company_id: UUID, schedule: MealScheduleDraft
    ) -> MealSchedule:
        company = await self.repository.by_id(company_id)
        if company is None:
            raise CompanyNotFoundError()
        if len(company.meal_schedules) >= 8:
            raise MealScheduleLimitError()
        try:
            return await self.repository.add_meal_schedule(company_id, schedule)
        except DuplicateMealScheduleError as error:
            raise MealScheduleConflictError from error

    async def update_meal_schedule(
        self,
        company_id: UUID,
        schedule_id: UUID,
        label: str | None,
        meal_time: time | None,
        weekdays: list[int] | None,
        active: bool | None,
        sort_order: int | None,
    ) -> MealSchedule:
        try:
            schedule = await self.repository.update_meal_schedule(
                company_id,
                schedule_id,
                label,
                meal_time,
                weekdays,
                active,
                sort_order,
            )
        except DuplicateMealScheduleError as error:
            raise MealScheduleConflictError from error
        if schedule is None:
            raise MealScheduleNotFoundError()
        return schedule

