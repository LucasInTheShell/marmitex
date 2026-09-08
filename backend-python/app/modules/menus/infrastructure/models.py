from decimal import Decimal
from uuid import UUID

from app.modules.menus.domain.entities import Menu, MenuItem, MenuItemImage


def menu_item_from_row(row: dict) -> MenuItem:
    return MenuItem(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        size_options=list(row["size_options"]),
        price=row["price"],
        size_prices={
            size: Decimal(str(price)) for size, price in row.get("size_prices", {}).items()
        },
        images=[
            MenuItemImage(
                id=UUID(image["id"]) if isinstance(image["id"], str) else image["id"],
                object_key=image["object_key"],
                sort_order=image["sort_order"],
                is_primary=image["is_primary"],
            )
            for image in row.get("images", [])
        ],
    )


def menu_from_row(row: dict) -> Menu:
    return Menu(**row)
