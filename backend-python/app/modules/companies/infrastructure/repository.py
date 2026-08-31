from __future__ import annotations

from datetime import time
from uuid import UUID

from psycopg import AsyncConnection
from psycopg.errors import UniqueViolation

from app.modules.companies.domain.entities import Company, MealSchedule, MealScheduleDraft
from app.modules.companies.domain.exceptions import (
    DuplicateCompanyEmailError,
    DuplicateMealScheduleError,
)
from app.modules.companies.infrastructure.models import (
    company_from_row,
    meal_schedule_from_row,
)


class PostgresCompanyRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self.connection = connection

    async def list(self) -> list[Company]:
        result = await self.connection.execute(
            """
            select c.id, c.name, c.active, c.created_at, a.email as access_email
            from companies c
            join lateral (
                select email
                from accounts
                where company_id = c.id and role = 'company'
                order by created_at, id
                limit 1
            ) a on true
            order by c.name
            """
        )
        rows = await result.fetchall()
        schedules = await self._schedules_by_company([row["id"] for row in rows])
        return [
            company_from_row(row, meal_schedules=schedules.get(row["id"], []))
            for row in rows
        ]

    async def by_id(self, company_id: UUID) -> Company | None:
        result = await self.connection.execute(
            """
            select c.id, c.name, c.active, c.created_at, a.email as access_email
            from companies c
            join lateral (
                select email
                from accounts
                where company_id = c.id and role = 'company'
                order by created_at, id
                limit 1
            ) a on true
            where c.id = %s
            """,
            (company_id,),
        )
        row = await result.fetchone()
        if row is None:
            return None
        schedules = await self._schedules_by_company([company_id])
        return company_from_row(row, meal_schedules=schedules.get(company_id, []))

    async def create(
        self,
        name: str,
        email: str,
        password_hash: str,
        meal_schedules: list[MealScheduleDraft],
    ) -> Company:
        try:
            async with self.connection.transaction():
                result = await self.connection.execute(
                    """
                    insert into companies (name) values (%s)
                    returning id, name, active, created_at
                    """,
                    (name,),
                )
                company = await result.fetchone()
                await self.connection.execute(
                    """
                    insert into accounts (name, email, password_hash, company_id, role)
                    values (%s, %s, %s, %s, 'company')
                    """,
                    (name, email, password_hash, company["id"]),
                )
                schedules = []
                for schedule in meal_schedules:
                    schedules.append(
                        await self._insert_meal_schedule(company["id"], schedule)
                    )
        except UniqueViolation as error:
            if error.diag.constraint_name == "company_meal_schedule_unique_label":
                raise DuplicateMealScheduleError from error
            raise DuplicateCompanyEmailError from error
        return company_from_row(company, email, schedules)

    async def add_meal_schedule(
        self, company_id: UUID, schedule: MealScheduleDraft
    ) -> MealSchedule:
        try:
            return await self._insert_meal_schedule(company_id, schedule)
        except UniqueViolation as error:
            raise DuplicateMealScheduleError from error

    async def update_meal_schedule(
        self,
        company_id: UUID,
        schedule_id: UUID,
        label: str | None,
        meal_time: time | None,
        weekdays: list[int] | None,
        active: bool | None,
        sort_order: int | None,
    ) -> MealSchedule | None:
        try:
            result = await self.connection.execute(
                """
                update company_meal_schedules
                set label = coalesce(%s, label),
                    meal_time = coalesce(%s, meal_time),
                    weekdays = coalesce(%s, weekdays),
                    active = coalesce(%s, active),
                    sort_order = coalesce(%s, sort_order),
                    updated_at = now()
                where id = %s and company_id = %s
                returning id, company_id, label, meal_time, weekdays, active, sort_order
                """,
                (
                    label,
                    meal_time,
                    weekdays,
                    active,
                    sort_order,
                    schedule_id,
                    company_id,
                ),
            )
            row = await result.fetchone()
        except UniqueViolation as error:
            raise DuplicateMealScheduleError from error
        return meal_schedule_from_row(row) if row else None

    async def _insert_meal_schedule(
        self, company_id: UUID, schedule: MealScheduleDraft
    ) -> MealSchedule:
        result = await self.connection.execute(
            """
            insert into company_meal_schedules
                (company_id, label, meal_time, weekdays, sort_order)
            values (%s, %s, %s, %s, %s)
            returning id, company_id, label, meal_time, weekdays, active, sort_order
            """,
            (
                company_id,
                schedule.label,
                schedule.meal_time,
                schedule.weekdays,
                schedule.sort_order,
            ),
        )
        return meal_schedule_from_row(await result.fetchone())

    async def _schedules_by_company(
        self, company_ids: list[UUID]
    ) -> dict[UUID, list[MealSchedule]]:
        if not company_ids:
            return {}
        result = await self.connection.execute(
            """
            select id, company_id, label, meal_time, weekdays, active, sort_order
            from company_meal_schedules
            where company_id = any(%s)
            order by company_id, sort_order, meal_time, label
            """,
            (company_ids,),
        )
        schedules: dict[UUID, list[MealSchedule]] = {}
        for row in await result.fetchall():
            schedule = meal_schedule_from_row(row)
            schedules.setdefault(schedule.company_id, []).append(schedule)
        return schedules

