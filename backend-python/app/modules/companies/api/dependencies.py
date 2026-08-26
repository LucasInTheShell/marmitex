from typing import Annotated

from fastapi import Depends

from app.api.dependencies import DatabaseConnection
from app.modules.auth.infrastructure.password import ArgonPasswordService
from app.modules.companies.application.services import CompanyApplicationService
from app.modules.companies.infrastructure.repository import PostgresCompanyRepository


def company_service(connection: DatabaseConnection) -> CompanyApplicationService:
    return CompanyApplicationService(
        PostgresCompanyRepository(connection), ArgonPasswordService()
    )


CompanyServiceDependency = Annotated[
    CompanyApplicationService, Depends(company_service)
]

