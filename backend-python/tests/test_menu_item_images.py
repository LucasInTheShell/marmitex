from decimal import Decimal
from io import BytesIO
from uuid import UUID

import pytest
from PIL import Image

from app.modules.menus.application.ports import ImageSource, ProcessedImage
from app.modules.menus.application.services import MenuApplicationService
from app.modules.menus.domain.entities import MenuItem, MenuItemImage
from app.modules.menus.domain.exceptions import InvalidMenuItemImageError
from app.modules.menus.infrastructure.image_processing import PillowImageProcessor


class FakeMenuRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, MenuItem] = {}

    async def list_items(self) -> list[MenuItem]:
        return list(self.items.values())

    async def item_by_id(self, item_id: UUID) -> MenuItem | None:
        return self.items.get(item_id)

    async def create_item(
        self,
        item_id: UUID,
        name: str,
        description: str | None,
        size_options: list[str],
        price: Decimal | None,
        images: list[MenuItemImage],
        size_prices: dict[str, Decimal] | None = None,
    ) -> MenuItem:
        item = MenuItem(item_id, name, description, size_options, price, images, size_prices or {})
        self.items[item_id] = item
        return item

    async def update_item(
        self,
        item_id: UUID,
        name: str,
        description: str | None,
        size_options: list[str],
        price: Decimal | None,
        images: list[MenuItemImage],
        size_prices: dict[str, Decimal] | None = None,
    ) -> MenuItem | None:
        if item_id not in self.items:
            return None
        item = MenuItem(item_id, name, description, size_options, price, images, size_prices or {})
        self.items[item_id] = item
        return item

    async def delete_item(self, item_id: UUID) -> MenuItem | None:
        return self.items.pop(item_id, None)


class FakeStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.deleted: list[str] = []

    async def upload(self, key: str, content: bytes, content_type: str) -> None:
        assert content_type == "image/webp"
        self.objects[key] = content

    async def delete(self, key: str) -> None:
        self.objects.pop(key, None)
        self.deleted.append(key)

    def public_url(self, key: str) -> str:
        return f"https://images.example/{key}"


class FakeImageProcessor:
    def process(self, source: ImageSource) -> ProcessedImage:
        if source.content == b"invalid":
            from app.modules.menus.application.ports import InvalidImageContentError

            raise InvalidImageContentError("Imagem inválida para o teste.")
        return ProcessedImage(b"webp", "image/webp", "webp", 800, 600)


def service(repository: FakeMenuRepository, storage: FakeStorage) -> MenuApplicationService:
    return MenuApplicationService(
        repository,  # type: ignore[arg-type]
        object(),  # type: ignore[arg-type]
        object(),  # type: ignore[arg-type]
        storage,
        FakeImageProcessor(),
    )


def source(content: bytes = b"original") -> ImageSource:
    return ImageSource(content, "image/png", "prato.png")


@pytest.mark.asyncio
async def test_create_gallery_choose_primary_add_remove_and_delete_images() -> None:
    repository = FakeMenuRepository()
    storage = FakeStorage()
    application = service(repository, storage)

    created = await application.create_item(
        "Lasanha", None, ["M"], Decimal("25.00"), [source(), source(b"second")], 1
    )
    item_id = created.id
    first, second = repository.items[item_id].images
    assert not first.is_primary
    assert second.is_primary
    assert created.image_url == f"https://images.example/{second.object_key}"
    assert len(created.images) == 2

    updated = await application.update_item(
        item_id,
        "Lasanha bolonhesa",
        None,
        ["M", "G"],
        Decimal("27.00"),
        [source(b"third")],
        [first.id],
        None,
        0,
    )
    retained, new_primary = repository.items[item_id].images
    assert retained.id == second.id
    assert new_primary.is_primary
    assert first.object_key in storage.deleted
    assert second.object_key not in storage.deleted
    assert updated.image_url == f"https://images.example/{new_primary.object_key}"

    without_image = await application.update_item(
        item_id,
        "Lasanha bolonhesa",
        None,
        ["M", "G"],
        Decimal("27.00"),
        [],
        [],
        None,
        None,
        True,
    )
    assert without_image.image_url is None
    assert second.object_key in storage.deleted
    assert new_primary.object_key in storage.deleted

    await application.delete_item(item_id)
    assert item_id not in repository.items


@pytest.mark.asyncio
async def test_invalid_image_is_rejected_before_database_write() -> None:
    repository = FakeMenuRepository()
    application = service(repository, FakeStorage())

    with pytest.raises(InvalidMenuItemImageError, match="Imagem inválida"):
        await application.create_item(
            "Lasanha", None, ["M"], Decimal("25.00"), [source(b"invalid")]
        )

    assert repository.items == {}


def test_pillow_processor_normalizes_and_limits_dimensions() -> None:
    original = Image.new("RGBA", (1800, 1200), (255, 0, 0, 120))
    buffer = BytesIO()
    original.save(buffer, format="PNG")

    processed = PillowImageProcessor().process(
        ImageSource(buffer.getvalue(), "image/png", "prato.png")
    )

    assert processed.content_type == "image/webp"
    assert processed.extension == "webp"
    assert processed.width <= 1200
    assert processed.height <= 900
    with Image.open(BytesIO(processed.content)) as result:
        assert result.format == "WEBP"
        assert result.mode == "RGB"
