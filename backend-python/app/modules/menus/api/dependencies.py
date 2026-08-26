from typing import Annotated

from fastapi import Depends

from app.api.dependencies import DatabaseConnection
from app.modules.menus.application.services import MenuApplicationService
from app.modules.menus.infrastructure.repository import PostgresMenuRepository


def menu_service(connection: DatabaseConnection) -> MenuApplicationService:
    return MenuApplicationService(PostgresMenuRepository(connection))


MenuServiceDependency = Annotated[MenuApplicationService, Depends(menu_service)]

