from datetime import UTC, date, datetime, time
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.modules.companies.domain.entities import Company, MealSchedule
from app.modules.menus.api.schemas import AvailableMenuResponse
from app.modules.menus.application.services import MenuApplicationService
from app.modules.menus.domain.entities import AvailableMenu, MenuItem
from app.modules.menus.domain.exceptions import InvalidMenuPeriodError
from app.modules.menus.infrastructure.models import menu_item_from_row
from app.modules.operations.domain.entities import OperationalSettings


class FakeMenuRepository:
    def __init__(self, menus: list[AvailableMenu]) -> None:
        self.menus = menus
        self.requested_period: tuple[date, date] | None = None

    async def published_between(
        self, start: date, end: date
    ) -> list[AvailableMenu]:
        self.requested_period = (start, end)
        return [menu for menu in self.menus if start <= menu.date <= end]


class FakeCompanyRepository:
    def __init__(self, company: Company) -> None:
        self.company = company

    async def by_id(self, company_id: UUID) -> Company | None:
        return self.company if company_id == self.company.id else None


class FakeSettingsRepository:
    async def get(self) -> OperationalSettings:
        return OperationalSettings(
            order_cutoff_lead_minutes=90,
            updated_at=datetime(2026, 8, 29, tzinfo=UTC),
        )


def menu(menu_date: date) -> AvailableMenu:
    return AvailableMenu(
        date=menu_date,
        items=[
            MenuItem(
                id=uuid4(),
                name="Frango grelhado",
                description="Arroz, feijão e salada",
                size_options=["P", "M", "G"],
                price=Decimal("24.90"),
            )
        ],
        available_schedules=[],
    )


def company_with_schedules(*meal_times: time) -> Company:
    company_id = uuid4()
    return Company(
        id=company_id,
        name="Empresa",
        active=True,
        created_at=datetime(2026, 8, 1, tzinfo=UTC),
        access_email="empresa@example.com",
        meal_schedules=[
            MealSchedule(
                id=uuid4(),
                company_id=company_id,
                label=f"Turno {index}",
                meal_time=meal_time,
                weekdays=[1, 2, 3, 4, 5],
                active=True,
                sort_order=index,
            )
            for index, meal_time in enumerate(meal_times, start=1)
        ],
    )


@pytest.mark.asyncio
async def test_today_remains_available_while_a_later_schedule_is_open() -> None:
    company = company_with_schedules(time(11, 30), time(13, 30))
    repository = FakeMenuRepository([menu(date(2026, 8, 31))])
    service = MenuApplicationService(
        repository,  # type: ignore[arg-type]
        FakeCompanyRepository(company),  # type: ignore[arg-type]
        FakeSettingsRepository(),  # type: ignore[arg-type]
    )

    available = await service.available(
        company.id,
        date(2026, 8, 31),
        date(2026, 8, 31),
        datetime.fromisoformat("2026-08-31T10:30:00-03:00"),
        "America/Sao_Paulo",
    )

    assert [item.date for item in available] == [date(2026, 8, 31)]
    assert [schedule.meal_time for schedule in available[0].available_schedules] == [
        time(13, 30)
    ]
    assert available[0].available_schedules[0].cutoff_at == datetime.fromisoformat(
        "2026-08-31T12:00:00-03:00"
    )


@pytest.mark.asyncio
async def test_today_disappears_when_every_schedule_reaches_cutoff() -> None:
    company = company_with_schedules(time(11, 30), time(13, 30))
    repository = FakeMenuRepository(
        [menu(date(2026, 8, 31)), menu(date(2026, 9, 1))]
    )
    service = MenuApplicationService(
        repository,  # type: ignore[arg-type]
        FakeCompanyRepository(company),  # type: ignore[arg-type]
        FakeSettingsRepository(),  # type: ignore[arg-type]
    )

    available = await service.available(
        company.id,
        date(2026, 8, 31),
        date(2026, 9, 1),
        datetime.fromisoformat("2026-08-31T12:00:00-03:00"),
        "America/Sao_Paulo",
    )

    assert [item.date for item in available] == [date(2026, 9, 1)]
    assert [
        schedule.meal_time for schedule in available[0].available_schedules
    ] == [time(11, 30), time(13, 30)]


@pytest.mark.asyncio
async def test_empty_menu_is_not_available() -> None:
    company = company_with_schedules(time(12))
    repository = FakeMenuRepository(
        [
            AvailableMenu(
                date=date(2026, 8, 31), items=[], available_schedules=[]
            )
        ]
    )
    service = MenuApplicationService(
        repository,  # type: ignore[arg-type]
        FakeCompanyRepository(company),  # type: ignore[arg-type]
        FakeSettingsRepository(),  # type: ignore[arg-type]
    )

    available = await service.available(
        company.id,
        date(2026, 8, 31),
        date(2026, 8, 31),
        datetime.fromisoformat("2026-08-31T09:00:00-03:00"),
        "America/Sao_Paulo",
    )

    assert available == []


@pytest.mark.asyncio
async def test_past_dates_and_days_without_company_service_are_hidden() -> None:
    company = company_with_schedules(time(12))
    repository = FakeMenuRepository(
        [menu(date(2026, 8, 28)), menu(date(2026, 8, 30)), menu(date(2026, 8, 31))]
    )
    service = MenuApplicationService(
        repository,  # type: ignore[arg-type]
        FakeCompanyRepository(company),  # type: ignore[arg-type]
        FakeSettingsRepository(),  # type: ignore[arg-type]
    )

    available = await service.available(
        company.id,
        date(2026, 8, 28),
        date(2026, 8, 31),
        datetime.fromisoformat("2026-08-29T09:00:00-03:00"),
        "America/Sao_Paulo",
    )

    assert repository.requested_period == (date(2026, 8, 29), date(2026, 8, 31))
    assert [item.date for item in available] == [date(2026, 8, 31)]


@pytest.mark.asyncio
async def test_available_menu_rejects_inverted_period() -> None:
    company = company_with_schedules(time(12))
    service = MenuApplicationService(
        FakeMenuRepository([]),  # type: ignore[arg-type]
        FakeCompanyRepository(company),  # type: ignore[arg-type]
        FakeSettingsRepository(),  # type: ignore[arg-type]
    )

    with pytest.raises(InvalidMenuPeriodError):
        await service.available(
            company.id,
            date(2026, 9, 4),
            date(2026, 8, 31),
            datetime.fromisoformat("2026-08-29T09:00:00-03:00"),
            "America/Sao_Paulo",
        )


def test_available_menu_response_uses_numeric_price() -> None:
    response = AvailableMenuResponse.model_validate(menu(date(2026, 8, 31)))

    assert response.model_dump(mode="json")["items"][0]["price"] == 24.9


def test_menu_item_mapper_ignores_columns_from_joined_menu() -> None:
    item_id = uuid4()

    item = menu_item_from_row(
        {
            "date": date(2026, 8, 31),
            "id": item_id,
            "name": "Frango grelhado",
            "description": None,
            "size_options": ["P", "M"],
            "price": Decimal("24.90"),
        }
    )

    assert item.id == item_id
    assert item.size_options == ["P", "M"]
