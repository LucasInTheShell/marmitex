from typing import Annotated

from fastapi import Depends

from app.api.dependencies import DatabaseConnection
from app.modules.operations.application.services import OperationalSettingsService
from app.modules.operations.infrastructure.repository import (
    PostgresOperationalSettingsRepository,
)


def operational_settings_service(
    connection: DatabaseConnection,
) -> OperationalSettingsService:
    return OperationalSettingsService(PostgresOperationalSettingsRepository(connection))


OperationalSettingsServiceDependency = Annotated[
    OperationalSettingsService, Depends(operational_settings_service)
]
