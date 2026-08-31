from datetime import UTC, date, datetime, time

import pytest

from app.modules.operations.application.services import OperationalSettingsService
from app.modules.operations.domain.cutoff import ordering_window
from app.modules.operations.domain.entities import OperationalSettings
from app.modules.operations.domain.exceptions import InvalidCutoffLeadError


class FakeOperationalSettingsRepository:
    def __init__(self) -> None:
        self.settings = OperationalSettings(
            order_cutoff_lead_minutes=90,
            updated_at=datetime(2026, 8, 28, tzinfo=UTC),
        )

    async def get(self) -> OperationalSettings:
        return self.settings

    async def update_cutoff_lead(self, minutes: int) -> OperationalSettings:
        self.settings = OperationalSettings(
            order_cutoff_lead_minutes=minutes,
            updated_at=datetime(2026, 8, 29, tzinfo=UTC),
        )
        return self.settings


@pytest.mark.asyncio
async def test_admin_setting_updates_the_global_cutoff_lead() -> None:
    repository = FakeOperationalSettingsRepository()
    service = OperationalSettingsService(repository)

    updated = await service.update_cutoff_lead(120)

    assert updated.order_cutoff_lead_minutes == 120
    assert (await service.get()).order_cutoff_lead_minutes == 120


@pytest.mark.asyncio
async def test_cutoff_lead_rejects_values_outside_one_day() -> None:
    service = OperationalSettingsService(FakeOperationalSettingsRepository())

    with pytest.raises(InvalidCutoffLeadError):
        await service.update_cutoff_lead(1441)


def test_ordering_window_is_relative_to_company_meal_time() -> None:
    window = ordering_window(
        date(2026, 8, 28),
        time(12, 30),
        lead_minutes=90,
        time_zone="America/Sao_Paulo",
    )

    assert window.scheduled_for.isoformat() == "2026-08-28T12:30:00-03:00"
    assert window.cutoff_at.isoformat() == "2026-08-28T11:00:00-03:00"
    assert window.accepts(datetime.fromisoformat("2026-08-28T10:59:59-03:00"))
    assert not window.accepts(datetime.fromisoformat("2026-08-28T11:00:00-03:00"))


def test_different_meal_times_produce_different_cutoffs() -> None:
    first = ordering_window(
        date(2026, 8, 28), time(12), 90, "America/Sao_Paulo"
    )
    second = ordering_window(
        date(2026, 8, 28), time(13, 30), 90, "America/Sao_Paulo"
    )

    assert first.cutoff_at.hour == 10
    assert first.cutoff_at.minute == 30
    assert second.cutoff_at.hour == 12
    assert second.cutoff_at.minute == 0
