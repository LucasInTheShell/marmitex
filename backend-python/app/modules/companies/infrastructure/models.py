from app.modules.companies.domain.entities import Company, MealSchedule


def meal_schedule_from_row(row: dict) -> MealSchedule:
    return MealSchedule(
        id=row["id"],
        company_id=row["company_id"],
        label=row["label"],
        meal_time=row["meal_time"],
        weekdays=list(row["weekdays"]),
        active=row["active"],
        sort_order=row["sort_order"],
    )


def company_from_row(
    row: dict,
    access_email: str | None = None,
    meal_schedules: list[MealSchedule] | None = None,
) -> Company:
    return Company(
        id=row["id"],
        name=row["name"],
        active=row["active"],
        created_at=row["created_at"],
        access_email=access_email or row["access_email"],
        meal_schedules=meal_schedules or [],
    )

