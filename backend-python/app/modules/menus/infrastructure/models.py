from app.modules.menus.domain.entities import Menu, MenuItem


def menu_item_from_row(row: dict) -> MenuItem:
    return MenuItem(**row)


def menu_from_row(row: dict) -> Menu:
    return Menu(**row)

