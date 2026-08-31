from typing import Annotated

from fastapi import Depends

from app.api.dependencies import DatabaseConnection
from app.modules.companies.infrastructure.repository import PostgresCompanyRepository
from app.modules.menus.application.services import MenuApplicationService
from app.modules.menus.infrastructure.repository import PostgresMenuRepository
from app.modules.operations.infrastructure.repository import (
    PostgresOperationalSettingsRepository,
)


def menu_service(connection: DatabaseConnection) -> MenuApplicationService:
    return MenuApplicationService(
        PostgresMenuRepository(connection),
        PostgresCompanyRepository(connection),
        PostgresOperationalSettingsRepository(connection),
    )


MenuServiceDependency = Annotated[MenuApplicationService, Depends(menu_service)]

