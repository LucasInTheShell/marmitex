from app.modules.operations.domain.entities import OperationalSettings
from app.modules.operations.domain.exceptions import InvalidCutoffLeadError
from app.modules.operations.domain.repositories import OperationalSettingsRepository


class OperationalSettingsService:
    def __init__(self, repository: OperationalSettingsRepository) -> None:
        self.repository = repository

    async def get(self) -> OperationalSettings:
        return await self.repository.get()

    async def update_cutoff_lead(self, minutes: int) -> OperationalSettings:
        if not 0 <= minutes <= 1440:
            raise InvalidCutoffLeadError()
        return await self.repository.update_cutoff_lead(minutes)
