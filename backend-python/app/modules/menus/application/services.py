import asyncio
import logging
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from app.modules.companies.domain.entities import MealSchedule
from app.modules.companies.domain.repositories import CompanyRepository
from app.modules.menus.application.dto import (
    AvailableMenuResult,
    MenuItemImageResult,
    MenuItemResult,
)
from app.modules.menus.application.ports import (
    MAX_MENU_ITEM_IMAGES,
    ImageProcessor,
    ImageSource,
    InvalidImageContentError,
    ObjectStorage,
    ObjectStorageOperationError,
)
from app.modules.menus.domain.entities import (
    AvailableMealSchedule,
    Menu,
    MenuItem,
    MenuItemImage,
)
from app.modules.menus.domain.exceptions import (
    EmptyMenuError,
    InvalidMenuItemImageError,
    InvalidMenuItemPriceError,
    InvalidMenuPeriodError,
    MenuItemNotFoundError,
    MenuItemStorageUnavailableError,
)
from app.modules.menus.domain.repositories import MenuRepository
from app.modules.operations.domain.cutoff import ordering_window
from app.modules.operations.domain.repositories import OperationalSettingsRepository

logger = logging.getLogger("mavi.menus")


class MenuApplicationService:
    def __init__(
        self,
        repository: MenuRepository,
        company_repository: CompanyRepository,
        settings_repository: OperationalSettingsRepository,
        storage: ObjectStorage,
        image_processor: ImageProcessor,
    ) -> None:
        self.repository = repository
        self.company_repository = company_repository
        self.settings_repository = settings_repository
        self.storage = storage
        self.image_processor = image_processor

    async def list_items(self) -> list[MenuItemResult]:
        return [self._result(item) for item in await self.repository.list_items()]

    async def create_item(
        self,
        name: str,
        description: str | None,
        size_options: list[str],
        price: Decimal | None,
        images: list[ImageSource],
        primary_image_index: int = 0,
        size_prices: dict[str, Decimal] | None = None,
    ) -> MenuItemResult:
        self._validate_prices(size_options, price, size_prices or {})
        item_id = uuid4()
        if len(images) > MAX_MENU_ITEM_IMAGES:
            raise InvalidMenuItemImageError(
                f"Um prato pode ter no máximo {MAX_MENU_ITEM_IMAGES} imagens."
            )
        if images and (primary_image_index < 0 or primary_image_index >= len(images)):
            raise InvalidMenuItemImageError("A imagem principal selecionada é inválida.")
        uploaded = await self._upload_images(item_id, images)
        gallery = self._normalize_gallery(
            uploaded,
            primary_image_id=self._new_primary_id(uploaded, primary_image_index),
        )
        try:
            item = await self.repository.create_item(
                item_id, name, description, size_options, price, gallery, size_prices or {}
            )
        except Exception:
            await self._delete_images_best_effort(uploaded)
            raise
        return self._result(item)

    async def update_item(
        self,
        item_id: UUID,
        name: str,
        description: str | None,
        size_options: list[str],
        price: Decimal | None,
        new_images: list[ImageSource],
        remove_image_ids: list[UUID],
        primary_image_id: UUID | None,
        primary_new_image_index: int | None,
        remove_all_images: bool = False,
        size_prices: dict[str, Decimal] | None = None,
    ) -> MenuItemResult:
        current = await self.repository.item_by_id(item_id)
        if current is None:
            raise MenuItemNotFoundError()
        if size_prices is None:
            size_prices = {s: p for s, p in current.size_prices.items() if s in size_options}
        self._validate_prices(size_options, price, size_prices)
        current_ids = {image.id for image in current.images}
        requested_removals = current_ids if remove_all_images else set(remove_image_ids)
        if not requested_removals.issubset(current_ids):
            raise InvalidMenuItemImageError("Uma das imagens selecionadas não pertence ao prato.")
        retained = [image for image in current.images if image.id not in requested_removals]
        retained_ids = {image.id for image in retained}
        if primary_image_id is not None and primary_new_image_index is not None:
            raise InvalidMenuItemImageError("Selecione apenas uma imagem principal.")
        if primary_image_id is not None and primary_image_id not in retained_ids:
            raise InvalidMenuItemImageError("A imagem principal selecionada é inválida.")
        if primary_new_image_index is not None and not (
            0 <= primary_new_image_index < len(new_images)
        ):
            raise InvalidMenuItemImageError("A imagem principal selecionada é inválida.")
        if len(retained) + len(new_images) > MAX_MENU_ITEM_IMAGES:
            raise InvalidMenuItemImageError(
                f"Um prato pode ter no máximo {MAX_MENU_ITEM_IMAGES} imagens."
            )
        uploaded = await self._upload_images(item_id, new_images, len(retained))
        selected_primary_id = primary_image_id
        if primary_new_image_index is not None:
            selected_primary_id = self._new_primary_id(uploaded, primary_new_image_index)
        if selected_primary_id is None:
            previous_primary = next(
                (image.id for image in retained if image.is_primary), None
            )
            selected_primary_id = previous_primary or (
                (retained + uploaded)[0].id if retained or uploaded else None
            )
        gallery = self._normalize_gallery(retained + uploaded, selected_primary_id)
        try:
            updated = await self.repository.update_item(
                item_id, name, description, size_options, price, gallery, size_prices or {}
            )
        except Exception:
            await self._delete_images_best_effort(uploaded)
            raise
        if updated is None:
            await self._delete_images_best_effort(uploaded)
            raise MenuItemNotFoundError()
        removed = [image for image in current.images if image.id in requested_removals]
        await self._delete_images_best_effort(removed)
        return self._result(updated)

    @staticmethod
    def _validate_prices(
        sizes: list[str], price: Decimal | None, size_prices: dict[str, Decimal]
    ) -> None:
        if not sizes or not set(sizes).issubset({"P", "M", "G"}):
            raise InvalidMenuItemPriceError()
        if not set(size_prices).issubset(sizes):
            raise InvalidMenuItemPriceError()
        if size_prices and price is None and set(size_prices) != set(sizes):
            raise InvalidMenuItemPriceError()
        values = list(size_prices.values()) + ([price] if price is not None else [])
        for value in values:
            if (
                not value.is_finite()
                or value < 0
                or value > Decimal("99999999.99")
                or value != value.quantize(Decimal("0.01"))
            ):
                raise InvalidMenuItemPriceError()

    async def delete_item(self, item_id: UUID) -> None:
        deleted = await self.repository.delete_item(item_id)
        if deleted is None:
            raise MenuItemNotFoundError()
        await self._delete_images_best_effort(deleted.images)

    async def list_week(self, start: date, end: date) -> list[Menu]:
        return await self.repository.between(start, end)

    async def available(
        self,
        company_id: UUID,
        start: date,
        end: date,
        now: datetime,
        time_zone: str,
    ) -> list[AvailableMenuResult]:
        if start > end:
            raise InvalidMenuPeriodError()
        company = await self.company_repository.by_id(company_id)
        if company is None or not company.active:
            return []
        settings = await self.settings_repository.get()
        today = now.date()
        menus = await self.repository.published_between(max(start, today), end)
        available_menus: list[AvailableMenuResult] = []
        for menu in menus:
            if not menu.items:
                continue
            available_schedules = self._available_schedules(
                menu.date,
                company.meal_schedules,
                settings.order_cutoff_lead_minutes,
                now,
                time_zone,
            )
            if available_schedules:
                available_menus.append(
                    AvailableMenuResult(
                        date=menu.date,
                        items=[self._result(item) for item in menu.items],
                        available_schedules=available_schedules,
                    )
                )
        return available_menus

    @staticmethod
    def _available_schedules(
        menu_date: date,
        schedules: list[MealSchedule],
        lead_minutes: int,
        now: datetime,
        time_zone: str,
    ) -> list[AvailableMealSchedule]:
        available: list[AvailableMealSchedule] = []
        ordered_schedules = sorted(
            schedules,
            key=lambda schedule: (
                schedule.sort_order,
                schedule.meal_time,
                schedule.label.casefold(),
            ),
        )
        for schedule in ordered_schedules:
            if not schedule.active or menu_date.isoweekday() not in schedule.weekdays:
                continue
            window = ordering_window(
                menu_date,
                schedule.meal_time,
                lead_minutes,
                time_zone,
            )
            if window.accepts(now):
                available.append(
                    AvailableMealSchedule(
                        id=schedule.id,
                        label=schedule.label,
                        meal_time=schedule.meal_time,
                        scheduled_for=window.scheduled_for,
                        cutoff_at=window.cutoff_at,
                    )
                )
        return available

    async def save_week(self, menus: list[tuple[date, list[UUID]]]) -> None:
        await self.repository.save_week(menus)

    async def publish(self, dates: list[date]) -> None:
        if await self.repository.publish(dates) == 0:
            raise EmptyMenuError()

    async def _upload_images(
        self,
        item_id: UUID,
        sources: list[ImageSource],
        start_order: int = 0,
    ) -> list[MenuItemImage]:
        uploaded: list[MenuItemImage] = []
        try:
            for offset, source in enumerate(sources):
                processed = await asyncio.to_thread(self.image_processor.process, source)
                image_id = uuid4()
                key = f"menu-items/{item_id}/{image_id}.{processed.extension}"
                await self.storage.upload(key, processed.content, processed.content_type)
                uploaded.append(
                    MenuItemImage(
                        id=image_id,
                        object_key=key,
                        sort_order=start_order + offset,
                        is_primary=False,
                    )
                )
        except InvalidImageContentError as error:
            await self._delete_images_best_effort(uploaded)
            raise InvalidMenuItemImageError(str(error)) from error
        except ObjectStorageOperationError as error:
            await self._delete_images_best_effort(uploaded)
            raise MenuItemStorageUnavailableError() from error
        return uploaded

    async def _delete_image_best_effort(self, key: str) -> None:
        try:
            await self.storage.delete(key)
        except ObjectStorageOperationError:
            logger.warning("menu_item_image_delete_failed key=%s", key, exc_info=True)

    async def _delete_images_best_effort(self, images: list[MenuItemImage]) -> None:
        for image in images:
            await self._delete_image_best_effort(image.object_key)

    @staticmethod
    def _new_primary_id(images: list[MenuItemImage], index: int) -> UUID | None:
        if not images:
            return None
        if index < 0 or index >= len(images):
            raise InvalidMenuItemImageError("A imagem principal selecionada é inválida.")
        return images[index].id

    @staticmethod
    def _normalize_gallery(
        images: list[MenuItemImage], primary_image_id: UUID | None
    ) -> list[MenuItemImage]:
        if images and primary_image_id not in {image.id for image in images}:
            raise InvalidMenuItemImageError("A imagem principal selecionada é inválida.")
        return [
            MenuItemImage(
                id=image.id,
                object_key=image.object_key,
                sort_order=index,
                is_primary=image.id == primary_image_id,
            )
            for index, image in enumerate(images)
        ]

    def _result(self, item: MenuItem) -> MenuItemResult:
        ordered_images = sorted(item.images, key=lambda image: image.sort_order)
        image_results = [
            MenuItemImageResult(
                id=image.id,
                url=self.storage.public_url(image.object_key),
                sort_order=image.sort_order,
                is_primary=image.is_primary,
            )
            for image in ordered_images
        ]
        primary = next((image for image in image_results if image.is_primary), None)
        return MenuItemResult(
            id=item.id,
            name=item.name,
            description=item.description,
            size_options=item.size_options,
            price=item.price,
            size_prices=item.size_prices,
            image_url=primary.url if primary else None,
            images=image_results,
        )
