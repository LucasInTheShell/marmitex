from app.modules.companies.domain.entities import Company


def company_from_row(row: dict, access_email: str | None = None) -> Company:
    return Company(
        id=row["id"],
        name=row["name"],
        active=row["active"],
        created_at=row["created_at"],
        access_email=access_email or row["access_email"],
    )

