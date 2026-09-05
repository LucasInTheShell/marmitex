from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from app.modules.companies.domain.repositories import CompanyRepository
from app.modules.menus.domain.repositories import MenuRepository
from app.modules.operations.domain.cutoff import ordering_window
from app.modules.operations.domain.repositories import OperationalSettingsRepository
from app.modules.orders.domain.entities import (
    Order,
    OrderDraft,
    OrderItemDraft,
    PaymentMethod,
    PaymentStatus,
)
from app.modules.orders.domain.exceptions import (
    CompanyCannotOrderError,
    IdempotencyConflictError,
    InvalidEmployeeCpfError,
    InvalidEmployeeDataError,
    InvalidEmployeePhoneError,
    InvalidMealScheduleError,
    InvalidOrderItemsError,
    InvalidOrderSizeError,
    MenuItemUnavailableError,
    MenuItemWithoutPriceError,
    MenuUnavailableError,
    OrderAlreadyExistsError,
    OrderingWindowClosedError,
)
from app.modules.orders.domain.repositories import (
    DuplicateOrderIdempotencyError,
    DuplicateOrderRecordError,
    OrderRepository,
)
from app.modules.orders.domain.rules import (
    MAX_ITEMS_PER_ORDER,
    MAX_QUANTITY_PER_ITEM,
    MAX_TOTAL_QUANTITY,
    normalized_cpf,
    normalized_phone,
)


@dataclass(frozen=True, slots=True)
class RequestedOrderItem:
    menu_item_id: UUID
    size: str
    quantity: int
    notes: str | None = None


@dataclass(frozen=True, slots=True)
class CreateOrderCommand:
    company_id: UUID
    date: date
    meal_schedule_id: UUID
    employee_name: str
    employee_phone: str
    employee_department: str
    employee_cpf: str
    employee_internal_id: str | None
    items: list[RequestedOrderItem]
    idempotency_key: str | None = None
    payment_method: PaymentMethod = PaymentMethod.PAY_ON_DELIVERY


class CreateOrder:
    def __init__(
        self,
        order_repository: OrderRepository,
        company_repository: CompanyRepository,
        menu_repository: MenuRepository,
        settings_repository: OperationalSettingsRepository,
    ) -> None:
        self.order_repository = order_repository
        self.company_repository = company_repository
        self.menu_repository = menu_repository
        self.settings_repository = settings_repository

    async def execute(
        self,
        command: CreateOrderCommand,
        now: datetime,
        time_zone: str,
    ) -> Order:
        employee_name = command.employee_name.strip()
        employee_department = command.employee_department.strip()
        if not employee_name or not employee_department:
            raise InvalidEmployeeDataError()
        employee_internal_id = (
            command.employee_internal_id.strip() or None if command.employee_internal_id else None
        )
        cpf = normalized_cpf(command.employee_cpf)
        if len(cpf) != 11:
            raise InvalidEmployeeCpfError()
        phone = normalized_phone(command.employee_phone)
        if not 10 <= len(phone) <= 15:
            raise InvalidEmployeePhoneError()
        idempotency_key = (
            command.idempotency_key.strip() or None if command.idempotency_key else None
        )
        fingerprint = self._fingerprint(
            command,
            employee_name,
            phone,
            employee_department,
            cpf,
            employee_internal_id,
        )
        if idempotency_key:
            existing = await self.order_repository.by_idempotency_key(
                command.company_id, idempotency_key
            )
            if existing is not None:
                return self._idempotent_result(existing, fingerprint)

        company = await self.company_repository.by_id(command.company_id)
        if company is None or not company.active:
            raise CompanyCannotOrderError()

        schedule = next(
            (
                candidate
                for candidate in company.meal_schedules
                if candidate.id == command.meal_schedule_id
            ),
            None,
        )
        if (
            schedule is None
            or not schedule.active
            or command.date.isoweekday() not in schedule.weekdays
        ):
            raise InvalidMealScheduleError()

        settings = await self.settings_repository.get()
        window = ordering_window(
            command.date,
            schedule.meal_time,
            settings.order_cutoff_lead_minutes,
            time_zone,
        )
        if not window.accepts(now):
            raise OrderingWindowClosedError()

        menus = await self.menu_repository.published_between(command.date, command.date)
        menu = next((candidate for candidate in menus if candidate.date == command.date), None)
        if menu is None or not menu.items:
            raise MenuUnavailableError()

        item_drafts = self._build_items(command.items, menu.items)
        total_price = sum((item.subtotal for item in item_drafts), start=Decimal("0.00"))
        draft = OrderDraft(
            company_id=command.company_id,
            date=command.date,
            meal_schedule_id=schedule.id,
            meal_schedule_label=schedule.label,
            scheduled_for=window.scheduled_for,
            cutoff_at=window.cutoff_at,
            employee_name=employee_name,
            employee_phone=phone,
            employee_department=employee_department,
            employee_cpf=cpf,
            employee_internal_id=employee_internal_id,
            total_price=total_price,
            idempotency_key=idempotency_key,
            request_fingerprint=fingerprint if idempotency_key else None,
            items=item_drafts,
            payment_method=command.payment_method,
            payment_status=(
                PaymentStatus.PENDING
                if command.payment_method is PaymentMethod.PIX
                else PaymentStatus.NOT_APPLICABLE
            ),
        )

        try:
            return await self.order_repository.create(draft)
        except DuplicateOrderIdempotencyError as error:
            assert idempotency_key is not None
            existing = await self.order_repository.by_idempotency_key(
                command.company_id, idempotency_key
            )
            if existing is None:
                raise IdempotencyConflictError from error
            return self._idempotent_result(existing, fingerprint)
        except DuplicateOrderRecordError as error:
            raise OrderAlreadyExistsError from error

    @staticmethod
    def _build_items(requested_items, menu_items) -> list[OrderItemDraft]:
        if not 1 <= len(requested_items) <= MAX_ITEMS_PER_ORDER:
            raise InvalidOrderItemsError(
                f"O pedido deve possuir entre 1 e {MAX_ITEMS_PER_ORDER} itens."
            )
        if any(
            item.quantity < 1 or item.quantity > MAX_QUANTITY_PER_ITEM for item in requested_items
        ):
            raise InvalidOrderItemsError()
        if sum(item.quantity for item in requested_items) > MAX_TOTAL_QUANTITY:
            raise InvalidOrderItemsError(
                f"O pedido pode conter no máximo {MAX_TOTAL_QUANTITY} marmitas."
            )

        menu_by_id = {item.id: item for item in menu_items}
        seen: set[tuple[UUID, str]] = set()
        drafts: list[OrderItemDraft] = []
        for requested in requested_items:
            menu_item = menu_by_id.get(requested.menu_item_id)
            if menu_item is None:
                raise MenuItemUnavailableError()
            size = requested.size.upper()
            if size not in menu_item.size_options:
                raise InvalidOrderSizeError()
            key = (menu_item.id, size)
            if key in seen:
                raise InvalidOrderItemsError(
                    "Itens repetidos com o mesmo prato e tamanho devem usar quantity."
                )
            seen.add(key)
            unit_price = menu_item.price_for_size(size)
            if unit_price is None:
                raise MenuItemWithoutPriceError()
            notes = requested.notes.strip() or None if requested.notes else None
            drafts.append(
                OrderItemDraft(
                    menu_item_id=menu_item.id,
                    item_name=menu_item.name,
                    item_description=menu_item.description,
                    size=size,
                    quantity=requested.quantity,
                    unit_price=unit_price,
                    subtotal=unit_price * requested.quantity,
                    notes=notes,
                )
            )
        return drafts

    @staticmethod
    def _fingerprint(
        command: CreateOrderCommand,
        employee_name: str,
        employee_phone: str,
        employee_department: str,
        employee_cpf: str,
        employee_internal_id: str | None,
    ) -> str:
        content = {
            "company_id": str(command.company_id),
            "date": command.date.isoformat(),
            "meal_schedule_id": str(command.meal_schedule_id),
            "employee_name": employee_name,
            "employee_phone": employee_phone,
            "employee_department": employee_department,
            "employee_cpf": employee_cpf,
            "employee_internal_id": employee_internal_id,
            "payment_method": command.payment_method.value,
            "items": [
                {
                    "menu_item_id": str(item.menu_item_id),
                    "size": item.size.upper(),
                    "quantity": item.quantity,
                    "notes": item.notes.strip() or None if item.notes else None,
                }
                for item in command.items
            ],
        }
        serialized = json.dumps(content, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode()).hexdigest()

    @staticmethod
    def _idempotent_result(existing: Order, fingerprint: str) -> Order:
        if existing.request_fingerprint != fingerprint:
            raise IdempotencyConflictError()
        return existing
