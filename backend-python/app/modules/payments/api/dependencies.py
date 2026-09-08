from typing import Annotated

from fastapi import Depends, Request

from app.api.dependencies import DatabaseConnection
from app.modules.companies.infrastructure.repository import PostgresCompanyRepository
from app.modules.orders.infrastructure.repository import PostgresOrderRepository
from app.modules.payments.application.services import PaymentApplicationService
from app.modules.payments.infrastructure.asaas_gateway import AsaasPaymentGateway
from app.modules.payments.infrastructure.repository import PostgresPaymentRepository


def payment_service(request: Request, connection: DatabaseConnection) -> PaymentApplicationService:
    return build_payment_service(request.app.state.settings, connection)


def build_payment_service(settings, connection) -> PaymentApplicationService:
    return PaymentApplicationService(
        PostgresOrderRepository(connection),
        PostgresCompanyRepository(connection),
        PostgresPaymentRepository(connection),
        AsaasPaymentGateway(
            api_key=settings.asaas_api_key or "",
            webhook_token=settings.asaas_webhook_token or "",
            api_url=settings.asaas_api_url,
            timeout_seconds=settings.asaas_request_timeout_seconds,
            user_agent=settings.asaas_user_agent,
        ),
    )


PaymentServiceDependency = Annotated[PaymentApplicationService, Depends(payment_service)]
