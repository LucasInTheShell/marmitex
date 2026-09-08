from app.modules.orders.domain.entities import (
    Order,
    OrderItem,
    PaymentMethod,
    PaymentStatus,
    ProductionStatus,
)


def order_item_from_row(row: dict) -> OrderItem:
    return OrderItem(
        id=row["id"],
        menu_item_id=row["menu_item_id"],
        item_name=row["item_name"],
        item_description=row["item_description"],
        size=row["size"],
        quantity=row["quantity"],
        unit_price=row["unit_price"],
        subtotal=row["subtotal"],
        notes=row["notes"],
    )


def order_from_row(row: dict, items: list[OrderItem]) -> Order:
    return Order(
        id=row["id"],
        order_number=row["order_number"],
        company_id=row["company_id"],
        company_name=row["company_name"],
        date=row["date"],
        meal_schedule_id=row.get("meal_schedule_id"),
        meal_schedule_label=row.get("meal_schedule_label"),
        scheduled_for=row.get("scheduled_for"),
        cutoff_at=row.get("cutoff_at"),
        employee_name=row["employee_name"],
        employee_phone=row["employee_phone"],
        employee_department=row["employee_department"],
        employee_cpf=row["employee_cpf"],
        employee_internal_id=row.get("employee_internal_id"),
        production_status=ProductionStatus(row["production_status"]),
        payment_method=(
            PaymentMethod(row["payment_method"])
            if row.get("payment_method") is not None
            else None
        ),
        payment_status=PaymentStatus(row["payment_status"]),
        total_price=row["total_price"],
        idempotency_key=row.get("idempotency_key"),
        request_fingerprint=row.get("request_fingerprint"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        cancelled_at=row.get("cancelled_at"),
        cancellation_reason=row.get("cancellation_reason"),
        items=items,
    )
