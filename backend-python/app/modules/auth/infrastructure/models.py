from app.modules.auth.domain.entities import Account, AccountRole


def account_from_row(row: dict) -> Account:
    return Account(
        id=row["id"],
        name=row["name"],
        email=row["email"],
        company_id=row["company_id"],
        role=AccountRole(row["role"]),
        password_hash=row.get("password_hash"),
    )

