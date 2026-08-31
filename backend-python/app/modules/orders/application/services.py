from __future__ import annotations

from datetime import date, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from app.modules.orders.domain.entities import (
    CompanyMealTimeProductionSummary,
    CompanyProductionSummary,
    DailyProductionSummary,
    MealTimeProductionSummary,
    Order,
    ProductionItemSummary,
    ProductionSizeSummary,
    ProductionStatus,
)
from app.modules.orders.domain.exceptions import (
    InvalidOrderPeriodError,
    InvalidProductionStatusTransitionError,
    OrderNotFoundError,
)
from app.modules.orders.domain.repositories import OrderRepository

ALLOWED_STATUS_TRANSITIONS = {
    ProductionStatus.PENDING: ProductionStatus.PRINTED,
    ProductionStatus.PRINTED: ProductionStatus.SEPARATED,
    ProductionStatus.SEPARATED: ProductionStatus.DELIVERED,
}


class OrderApplicationService:
    def __init__(self, repository: OrderRepository) -> None:
        self.repository = repository

    async def list(
        self,
        start: date,
        end: date,
        company_id: UUID | None = None,
        production_status: ProductionStatus | None = None,
    ) -> list[Order]:
        self._validate_period(start, end)
        return await self.repository.list(start, end, company_id, production_status)

    async def by_id(self, order_id: UUID, company_id: UUID | None = None) -> Order:
        order = await self.repository.by_id(order_id)
        if order is None or (company_id is not None and order.company_id != company_id):
            raise OrderNotFoundError()
        return order

    async def production_board(self, board_date: date) -> list[Order]:
        orders = await self.repository.list(board_date, board_date)
        return [
            order
            for order in orders
            if order.production_status is not ProductionStatus.CANCELLED
        ]

    async def production_summary(
        self, summary_date: date, time_zone: str
    ) -> DailyProductionSummary:
        orders = await self.repository.list(summary_date, summary_date)
        included_orders = [
            order for order in orders if order.production_status is not ProductionStatus.CANCELLED
        ]
        groups: dict[datetime | None, dict] = {}
        company_groups: dict[UUID, dict] = {}
        for order in included_orders:
            group = groups.setdefault(
                order.scheduled_for,
                {
                    "schedule_ids": [],
                    "schedule_labels": [],
                    "total_orders": 0,
                    "total_meals": 0,
                    "items": {},
                },
            )
            group["total_orders"] += 1
            if (
                order.meal_schedule_id is not None
                and order.meal_schedule_id not in group["schedule_ids"]
            ):
                group["schedule_ids"].append(order.meal_schedule_id)
            if (
                order.meal_schedule_label
                and order.meal_schedule_label not in group["schedule_labels"]
            ):
                group["schedule_labels"].append(order.meal_schedule_label)
            for item in order.items:
                group["total_meals"] += item.quantity
                item_group = group["items"].setdefault(
                    item.menu_item_id,
                    {"item_name": item.item_name, "total_quantity": 0, "sizes": {}},
                )
                item_group["total_quantity"] += item.quantity
                item_group["sizes"][item.size] = (
                    item_group["sizes"].get(item.size, 0) + item.quantity
                )

            company_group = company_groups.setdefault(
                order.company_id,
                {
                    "company_name": order.company_name,
                    "total_orders": 0,
                    "total_meals": 0,
                    "meal_times": {},
                    "items": {},
                },
            )
            company_group["total_orders"] += 1
            company_time_group = company_group["meal_times"].setdefault(
                order.scheduled_for,
                {"total_orders": 0, "total_meals": 0},
            )
            company_time_group["total_orders"] += 1
            for item in order.items:
                company_group["total_meals"] += item.quantity
                company_time_group["total_meals"] += item.quantity
                company_item_group = company_group["items"].setdefault(
                    item.menu_item_id,
                    {"item_name": item.item_name, "total_quantity": 0, "sizes": {}},
                )
                company_item_group["total_quantity"] += item.quantity
                company_item_group["sizes"][item.size] = (
                    company_item_group["sizes"].get(item.size, 0) + item.quantity
                )

        size_order = {"P": 0, "M": 1, "G": 2}
        meal_times: list[MealTimeProductionSummary] = []
        for scheduled_for, group in sorted(
            groups.items(),
            key=lambda entry: (
                entry[0] is None,
                entry[0].timestamp() if entry[0] is not None else float("inf"),
            ),
        ):
            items = [
                ProductionItemSummary(
                    menu_item_id=menu_item_id,
                    item_name=item_group["item_name"],
                    total_quantity=item_group["total_quantity"],
                    sizes=[
                        ProductionSizeSummary(size=size, quantity=quantity)
                        for size, quantity in sorted(
                            item_group["sizes"].items(),
                            key=lambda entry: size_order.get(entry[0], 99),
                        )
                    ],
                )
                for menu_item_id, item_group in group["items"].items()
            ]
            meal_times.append(
                MealTimeProductionSummary(
                    scheduled_for=scheduled_for,
                    meal_time=self._local_meal_time(scheduled_for, time_zone),
                    schedule_ids=group["schedule_ids"],
                    schedule_labels=group["schedule_labels"],
                    total_orders=group["total_orders"],
                    total_meals=group["total_meals"],
                    items=items,
                )
            )

        companies: list[CompanyProductionSummary] = []
        for company_id, group in sorted(
            company_groups.items(),
            key=lambda entry: entry[1]["company_name"].casefold(),
        ):
            company_meal_times = [
                CompanyMealTimeProductionSummary(
                    scheduled_for=scheduled_for,
                    meal_time=self._local_meal_time(scheduled_for, time_zone),
                    total_orders=time_group["total_orders"],
                    total_meals=time_group["total_meals"],
                )
                for scheduled_for, time_group in sorted(
                    group["meal_times"].items(),
                    key=lambda entry: (
                        entry[0] is None,
                        entry[0].timestamp() if entry[0] is not None else float("inf"),
                    ),
                )
            ]
            company_items = [
                ProductionItemSummary(
                    menu_item_id=menu_item_id,
                    item_name=item_group["item_name"],
                    total_quantity=item_group["total_quantity"],
                    sizes=[
                        ProductionSizeSummary(size=size, quantity=quantity)
                        for size, quantity in sorted(
                            item_group["sizes"].items(),
                            key=lambda entry: size_order.get(entry[0], 99),
                        )
                    ],
                )
                for menu_item_id, item_group in group["items"].items()
            ]
            companies.append(
                CompanyProductionSummary(
                    company_id=company_id,
                    company_name=group["company_name"],
                    total_orders=group["total_orders"],
                    total_meals=group["total_meals"],
                    meal_times=company_meal_times,
                    items=company_items,
                )
            )
        return DailyProductionSummary(
            date=summary_date,
            total_orders=len(included_orders),
            total_meals=sum(group.total_meals for group in meal_times),
            meal_times=meal_times,
            companies=companies,
        )

    async def update_production_status(
        self,
        order_id: UUID,
        new_status: ProductionStatus,
        now: datetime,
    ) -> Order:
        order = await self.repository.by_id(order_id, for_update=True)
        if order is None:
            raise OrderNotFoundError()
        if ALLOWED_STATUS_TRANSITIONS.get(order.production_status) is not new_status:
            raise InvalidProductionStatusTransitionError()
        updated = await self.repository.update_status(
            order_id, order.production_status, new_status, now
        )
        if not updated:
            raise InvalidProductionStatusTransitionError()
        result = await self.repository.by_id(order_id)
        if result is None:
            raise OrderNotFoundError()
        return result

    @staticmethod
    def _validate_period(start: date, end: date) -> None:
        if start > end or end - start > timedelta(days=30):
            raise InvalidOrderPeriodError()

    @staticmethod
    def _local_meal_time(scheduled_for: datetime | None, time_zone: str):
        if scheduled_for is None:
            return None
        return (
            scheduled_for.astimezone(ZoneInfo(time_zone))
            .timetz()
            .replace(tzinfo=None)
        )
