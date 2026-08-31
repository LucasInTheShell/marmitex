from app.core.config import Settings
from app.main import create_app
from tests.test_health import FakeDatabase


def test_composition_root_exposes_the_frontend_contracts() -> None:
    app = create_app(
        Settings(database_url="postgresql://local/test"),
        FakeDatabase(),  # type: ignore[arg-type]
    )

    paths = set(app.openapi()["paths"])

    assert "/api/v1/auth/login" in paths
    assert "/api/v1/auth/me" in paths
    assert "/api/v1/accounts" in paths
    assert "/api/v1/companies" in paths
    assert "/api/v1/companies/me" in paths
    assert "/api/v1/companies/{company_id}/meal-schedules" in paths
    assert "/api/v1/menu-items" in paths
    assert "/api/v1/menus/week" in paths
    assert "/api/v1/menus/available" in paths
    assert "/api/v1/operational-settings" in paths
