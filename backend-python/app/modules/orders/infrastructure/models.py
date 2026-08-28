from app.modules.orders.domain.entities import Order, ProductionStatus


def order_from_row(row: dict) -> Order:
    return Order(
        id=row["id"],
        company_id=row["company_id"],
        date=row["date"],
        menu_item_id=row["menu_item_id"],
        size=row["size"],
        employee_name=row["employee_name"],
        employee_phone=row["employee_phone"],
        employee_department=row["employee_department"],
        employee_cpf=row["employee_cpf"],
        production_status=ProductionStatus(row["production_status"]),
        created_at=row["created_at"],
    )

