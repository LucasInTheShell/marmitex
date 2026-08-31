from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from app.modules.companies.domain.entities import MealSchedule
from app.modules.companies.domain.repositories import CompanyRepository
from app.modules.menus.domain.entities import (
    AvailableMealSchedule,
    AvailableMenu,
    Menu,
    MenuItem,
)
from app.modules.menus.domain.exceptions import EmptyMenuError, InvalidMenuPeriodError
from app.modules.menus.domain.repositories import MenuRepository
from app.modules.operations.domain.cutoff import ordering_window
from app.modules.operations.domain.repositories import OperationalSettingsRepository


class MenuApplicationService:
    def __init__(
        self,
        repository: MenuRepository,
        company_repository: CompanyRepository,
        settings_repository: OperationalSettingsRepository,
    ) -> None:
        self.repository = repository
        self.company_repository = company_repository
        self.settings_repository = settings_repository

    async def list_items(self) -> list[MenuItem]:
        return await self.repository.list_items()

    async def create_item(
        self,
        name: str,
        description: str | None,
        size_options: list[str],
        price: Decimal | None,
    ) -> MenuItem:
        return await self.repository.create_item(
            name, description, size_options, price
        )

    async def list_week(self, start: date, end: date) -> list[Menu]:
        return await self.repository.between(start, end)

    async def available(
        self,
        company_id: UUID,
        start: date,
        end: date,
        now: datetime,
        time_zone: str,
    ) -> list[AvailableMenu]:
        if start > end:
            raise InvalidMenuPeriodError()
        company = await self.company_repository.by_id(company_id)
        if company is None or not company.active:
            return []
        settings = await self.settings_repository.get()
        today = now.date()
        menus = await self.repository.published_between(max(start, today), end)
        available_menus: list[AvailableMenu] = []
        for menu in menus:
            if not menu.items:
                continue
            available_schedules = self._available_schedules(
                menu.date,
                company.meal_schedules,
                settings.order_cutoff_lead_minutes,
                now,
                time_zone,
            )
            if available_schedules:
                available_menus.append(
                    AvailableMenu(
                        date=menu.date,
                        items=menu.items,
                        available_schedules=available_schedules,
                    )
                )
        return available_menus

    @staticmethod
    def _available_schedules(
        menu_date: date,
        schedules: list[MealSchedule],
        lead_minutes: int,
        now: datetime,
        time_zone: str,
    ) -> list[AvailableMealSchedule]:
        available: list[AvailableMealSchedule] = []
        ordered_schedules = sorted(
            schedules,
            key=lambda schedule: (
                schedule.sort_order,
                schedule.meal_time,
                schedule.label.casefold(),
            ),
        )
        for schedule in ordered_schedules:
            if not schedule.active or menu_date.isoweekday() not in schedule.weekdays:
                continue
            window = ordering_window(
                menu_date,
                schedule.meal_time,
                lead_minutes,
                time_zone,
            )
            if window.accepts(now):
                available.append(
                    AvailableMealSchedule(
                        id=schedule.id,
                        label=schedule.label,
                        meal_time=schedule.meal_time,
                        scheduled_for=window.scheduled_for,
                        cutoff_at=window.cutoff_at,
                    )
                )
        return available

    async def save_week(self, menus: list[tuple[date, list[UUID]]]) -> None:
        await self.repository.save_week(menus)

    async def publish(self, dates: list[date]) -> None:
        if await self.repository.publish(dates) == 0:
            raise EmptyMenuError()

