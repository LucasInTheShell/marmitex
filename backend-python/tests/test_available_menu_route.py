from datetime import date, datetime, time
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.modules.auth.api.dependencies import current_account
from app.modules.auth.domain.entities import Account, AccountRole
from app.modules.menus.api.dependencies import menu_service
from app.modules.menus.application.dto import MenuItemResult
from app.modules.menus.domain.entities import (
    AvailableMealSchedule,
    AvailableMenu,
    Menu,
    MenuItem,
)
from tests.test_health import FakeDatabase


class FakeMenuService:
    def __init__(self) -> None:
        self.saved_menus: list[tuple[date, list]] = []
        self.schedule_id = uuid4()
        self.created_item: tuple | None = None

    async def create_item(self, *values) -> MenuItemResult:
        self.created_item = values
        return MenuItemResult(
            id=uuid4(),
            name=values[0],
            description=values[1],
            size_options=values[2],
            price=values[3],
            image_url="https://images.example/menu-items/item/image.webp",
            images=[],
        )

    async def available(self, *_) -> list[AvailableMenu]:
        return [
            AvailableMenu(
                date=date(2026, 8, 31),
                items=[
                    MenuItem(
                        id=uuid4(),
                        name="Frango grelhado",
                        description="Arroz, feijão e salada",
                        size_options=["P", "M", "G"],
                        price=Decimal("24.90"),
                    )
                ],
                available_schedules=[
                    AvailableMealSchedule(
                        id=self.schedule_id,
                        label="Almoço",
                        meal_time=time(13),
                        scheduled_for=datetime.fromisoformat(
                            "2026-08-31T13:00:00-03:00"
                        ),
                        cutoff_at=datetime.fromisoformat(
                            "2026-08-31T11:30:00-03:00"
                        ),
                    )
                ],
            )
        ]

    async def list_week(self, *_: date) -> list[Menu]:
        return []

    async def save_week(self, menus: list[tuple[date, list]]) -> None:
        self.saved_menus = menus


def account(role: AccountRole) -> Account:
    return Account(
        id=uuid4(),
        name="Conta",
        email="conta@example.com",
        company_id=uuid4() if role is AccountRole.COMPANY else None,
        role=role,
    )


def app_for(role: AccountRole, service: FakeMenuService):
    app = create_app(
        Settings(database_url="postgresql://local/test"),
        FakeDatabase(),  # type: ignore[arg-type]
    )
    app.dependency_overrides[current_account] = lambda: account(role)
    app.dependency_overrides[menu_service] = lambda: service
    return app


def test_company_reads_published_menu_items_as_complete_objects() -> None:
    service = FakeMenuService()
    app = app_for(AccountRole.COMPANY, service)

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/menus/available?start=2026-08-31&end=2026-09-04"
        )

    assert response.status_code == 200
    assert response.json()[0]["date"] == "2026-08-31"
    assert response.json()[0]["items"][0]["name"] == "Frango grelhado"
    assert response.json()[0]["items"][0]["price"] == 24.9
    assert response.json()[0]["available_schedules"][0] == {
        "id": str(service.schedule_id),
        "label": "Almoço",
        "meal_time": "13:00:00",
        "scheduled_for": "2026-08-31T13:00:00-03:00",
        "cutoff_at": "2026-08-31T11:30:00-03:00",
    }
    assert "menu_item_ids" not in response.json()[0]


def test_admin_cannot_use_company_available_menu_endpoint() -> None:
    app = app_for(AccountRole.ADMIN, FakeMenuService())

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/menus/available?start=2026-08-31&end=2026-09-04"
        )

    assert response.status_code == 403


def test_admin_can_still_read_and_edit_menus() -> None:
    service = FakeMenuService()
    app = app_for(AccountRole.ADMIN, service)
    item_id = uuid4()

    with TestClient(app) as client:
        read_response = client.get(
            "/api/v1/menus?start=2026-08-31&end=2026-09-04"
        )
        edit_response = client.put(
            "/api/v1/menus/week",
            json={
                "menus": [
                    {
                        "date": "2026-08-31",
                        "menu_item_ids": [str(item_id)],
                    }
                ]
            },
        )

    assert read_response.status_code == 200
    assert edit_response.status_code == 204
    assert service.saved_menus == [(date(2026, 8, 31), [item_id])]


def test_company_has_read_only_menu_access() -> None:
    app = app_for(AccountRole.COMPANY, FakeMenuService())
    item_id = uuid4()

    with TestClient(app) as client:
        available_response = client.get(
            "/api/v1/menus/available?start=2026-08-31&end=2026-09-04"
        )
        admin_read_response = client.get(
            "/api/v1/menus?start=2026-08-31&end=2026-09-04"
        )
        edit_response = client.put(
            "/api/v1/menus/week",
            json={
                "menus": [
                    {
                        "date": "2026-08-31",
                        "menu_item_ids": [str(item_id)],
                    }
                ]
            },
        )

    assert available_response.status_code == 200
    assert admin_read_response.status_code == 403
    assert edit_response.status_code == 403


def test_admin_creates_menu_item_with_multiple_images_and_primary_selection() -> None:
    service = FakeMenuService()
    app = app_for(AccountRole.ADMIN, service)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/menu-items",
            data={
                "name": "Lasanha",
                "description": "Molho bolonhesa",
                "size_options": ["M", "G"],
                "price": "26.90",
                "primary_image_index": "1",
            },
            files=[
                ("images", ("lasanha.png", b"first-image", "image/png")),
                ("images", ("lasanha-2.jpg", b"second-image", "image/jpeg")),
            ],
        )

    assert response.status_code == 201
    assert response.json()["image_url"].endswith("image.webp")
    assert service.created_item is not None
    assert service.created_item[0:4] == (
        "Lasanha",
        "Molho bolonhesa",
        ["M", "G"],
        Decimal("26.90"),
    )
    assert service.created_item[4][0].filename == "lasanha.png"
    assert service.created_item[4][1].filename == "lasanha-2.jpg"
    assert service.created_item[5] == 1
