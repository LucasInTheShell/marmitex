from __future__ import annotations

from datetime import time
from typing import Protocol
from uuid import UUID

from app.modules.companies.domain.entities import Company, MealSchedule, MealScheduleDraft


class CompanyRepository(Protocol):
    async def list(self) -> list[Company]: ...

    async def by_id(self, company_id: UUID) -> Company | None: ...

    async def create(
        self,
        name: str,
        email: str,
        password_hash: str,
        meal_schedules: list[MealScheduleDraft],
    ) -> Company: ...

    async def add_meal_schedule(
        self, company_id: UUID, schedule: MealScheduleDraft
    ) -> MealSchedule: ...

    async def update_meal_schedule(
        self,
        company_id: UUID,
        schedule_id: UUID,
        label: str | None,
        meal_time: time | None,
        weekdays: list[int] | None,
        active: bool | None,
        sort_order: int | None,
    ) -> MealSchedule | None: ...


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

