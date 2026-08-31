from app.modules.menus.domain.entities import Menu, MenuItem


def menu_item_from_row(row: dict) -> MenuItem:
    return MenuItem(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        size_options=list(row["size_options"]),
        price=row["price"],
    )


def menu_from_row(row: dict) -> Menu:
    return Menu(**row)

