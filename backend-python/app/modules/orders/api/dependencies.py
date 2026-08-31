from typing import Annotated

from fastapi import Depends

from app.api.dependencies import DatabaseConnection
from app.modules.companies.infrastructure.repository import PostgresCompanyRepository
from app.modules.menus.infrastructure.repository import PostgresMenuRepository
from app.modules.operations.infrastructure.repository import (
    PostgresOperationalSettingsRepository,
)
from app.modules.orders.application.cancel_order import CancelOrder
from app.modules.orders.application.create_order import CreateOrder
from app.modules.orders.application.services import OrderApplicationService
from app.modules.orders.infrastructure.repository import PostgresOrderRepository


def create_order_use_case(connection: DatabaseConnection) -> CreateOrder:
    return CreateOrder(
        PostgresOrderRepository(connection),
        PostgresCompanyRepository(connection),
        PostgresMenuRepository(connection),
        PostgresOperationalSettingsRepository(connection),
    )


def cancel_order_use_case(connection: DatabaseConnection) -> CancelOrder:
    return CancelOrder(PostgresOrderRepository(connection))


def order_service(connection: DatabaseConnection) -> OrderApplicationService:
    return OrderApplicationService(PostgresOrderRepository(connection))


CreateOrderDependency = Annotated[CreateOrder, Depends(create_order_use_case)]
CancelOrderDependency = Annotated[CancelOrder, Depends(cancel_order_use_case)]
OrderServiceDependency = Annotated[OrderApplicationService, Depends(order_service)]
