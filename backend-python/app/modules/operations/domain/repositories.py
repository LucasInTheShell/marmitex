from typing import Protocol

from app.modules.operations.domain.entities import OperationalSettings


class OperationalSettingsRepository(Protocol):
    async def get(self) -> OperationalSettings: ...

    async def update_cutoff_lead(self, minutes: int) -> OperationalSettings: ...
