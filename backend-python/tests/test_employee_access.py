from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import create_app
from app.modules.employees.api.dependencies import current_employee
from app.modules.employees.api.schemas import EmployeeOrderCreateRequest
from app.modules.employees.application.services import EmployeeAccessService
from app.modules.employees.domain.entities import Employee
from app.modules.employees.domain.exceptions import EmployeeAccessDeniedError
from app.modules.orders.api.dependencies import create_order_use_case
from tests.test_health import FakeDatabase
from tests.test_order_routes import FakeCreateOrder, sample_order


class FakeEmployeeRepository:
    def __init__(self, employee: Employee | None) -> None:
        self.employee = employee
        self.created_session = None
        self.revoked_hash = None

    async def by_cpf(self, cpf: str):
        return self.employee if self.employee and self.employee.cpf == cpf else None

    async def by_session_hash(self, token_hash: str):
        return self.employee if token_hash == "hashed-session" else None

    async def create_session(self, employee_id, token_hash, expires_at) -> None:
        self.created_session = (employee_id, token_hash, expires_at)

    async def revoke_session(self, token_hash: str) -> None:
        self.revoked_hash = token_hash


class FakeSessions:
    def create(self) -> str:
        return "session"

    def hash(self, token: str) -> str:
        return f"hashed-{token}"


def employee() -> Employee:
    now = datetime.now(UTC)
    return Employee(
        id=uuid4(),
        company_id=uuid4(),
        company_name="Empresa",
        name="Maria",
        cpf="12345678901",
        phone="11999999999",
        department="Financeiro",
        internal_id="42",
        active=True,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_cpf_access_issues_a_short_lived_opaque_session() -> None:
    registered = employee()
    repository = FakeEmployeeRepository(registered)
    service = EmployeeAccessService(repository, FakeSessions(), session_ttl_hours=12)

    token, expires_at, authenticated = await service.login("123.456.789-01")

    assert token == "session"
    assert authenticated == registered
    assert repository.created_session[0] == registered.id
    assert repository.created_session[1] == "hashed-session"
    assert repository.created_session[1] != token
    assert expires_at == repository.created_session[2]


@pytest.mark.asyncio
@pytest.mark.parametrize("cpf", ["123", "99999999999"])
async def test_cpf_access_uses_the_same_error_for_invalid_or_unknown_cpf(cpf: str) -> None:
    service = EmployeeAccessService(
        FakeEmployeeRepository(None), FakeSessions(), session_ttl_hours=12
    )

    with pytest.raises(EmployeeAccessDeniedError) as captured:
        await service.login(cpf)

    assert captured.value.status_code == 401
    assert captured.value.code == "invalid_employee_access"


def test_employee_order_payload_cannot_override_identity_or_company() -> None:
    with pytest.raises(ValidationError):
        EmployeeOrderCreateRequest.model_validate(
            {
                "date": "2026-09-02",
                "meal_schedule_id": str(uuid4()),
                "employee_name": "Pessoa forjada",
                "company_id": str(uuid4()),
                "items": [
                    {
                        "menu_item_id": str(uuid4()),
                        "size": "M",
                        "quantity": 1,
                    }
                ],
            }
        )


def test_employee_order_uses_identity_and_company_from_employee_session() -> None:
    authenticated = employee()
    order = sample_order(authenticated.company_id)
    use_case = FakeCreateOrder(order)
    app = create_app(
        Settings(database_url="postgresql://local/test"),
        FakeDatabase(),  # type: ignore[arg-type]
    )
    app.dependency_overrides[current_employee] = lambda: authenticated
    app.dependency_overrides[create_order_use_case] = lambda: use_case

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/employee/orders",
            headers={"Idempotency-Key": "employee-checkout-1"},
            json={
                "date": "2026-08-31",
                "meal_schedule_id": str(order.meal_schedule_id),
                "items": [
                    {
                        "menu_item_id": str(order.items[0].menu_item_id),
                        "size": "M",
                        "quantity": 2,
                    }
                ],
            },
        )

    assert response.status_code == 201
    assert use_case.command.company_id == authenticated.company_id
    assert use_case.command.employee_name == authenticated.name
    assert use_case.command.employee_phone == authenticated.phone
    assert use_case.command.employee_cpf == authenticated.cpf
    assert use_case.command.employee_department == authenticated.department
    assert use_case.command.idempotency_key == "employee-checkout-1"
