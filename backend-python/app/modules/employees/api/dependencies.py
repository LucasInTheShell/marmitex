from typing import Annotated

from fastapi import Depends, Request

from app.api.dependencies import DatabaseConnection
from app.core.security import bearer_token
from app.modules.auth.api.dependencies import Credentials
from app.modules.auth.infrastructure.session import OpaqueSessionService
from app.modules.employees.application.services import (
    EmployeeAccessService,
    EmployeeManagementService,
)
from app.modules.employees.domain.entities import Employee
from app.modules.employees.domain.exceptions import EmployeeAccessDeniedError
from app.modules.employees.infrastructure.repository import PostgresEmployeeRepository


def employee_access_service(
    request: Request, connection: DatabaseConnection
) -> EmployeeAccessService:
    return EmployeeAccessService(
        PostgresEmployeeRepository(connection),
        OpaqueSessionService(),
        request.app.state.settings.employee_session_ttl_hours,
    )


def employee_management_service(
    connection: DatabaseConnection,
) -> EmployeeManagementService:
    return EmployeeManagementService(PostgresEmployeeRepository(connection))


EmployeeAccessServiceDependency = Annotated[
    EmployeeAccessService, Depends(employee_access_service)
]
EmployeeManagementServiceDependency = Annotated[
    EmployeeManagementService, Depends(employee_management_service)
]


async def current_employee(
    credentials: Credentials, service: EmployeeAccessServiceDependency
) -> Employee:
    token = bearer_token(credentials)
    if not token:
        raise EmployeeAccessDeniedError()
    return await service.authenticate(token)


CurrentEmployee = Annotated[Employee, Depends(current_employee)]
