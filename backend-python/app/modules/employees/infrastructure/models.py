from app.modules.employees.domain.entities import Employee


def employee_from_row(row) -> Employee:
    return Employee(
        id=row["id"],
        company_id=row["company_id"],
        company_name=row["company_name"],
        name=row["name"],
        cpf=row["cpf"],
        phone=row["phone"],
        department=row["department"],
        internal_id=row["internal_id"],
        active=row["active"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
