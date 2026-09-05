from app.core.exceptions import ApplicationError


class EmptyMenuError(ApplicationError):
    def __init__(self) -> None:
        super().__init__("empty_menu", "Nenhum cardápio preenchido foi encontrado.", 422)


class InvalidMenuItemPriceError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            "invalid_menu_item_price",
            "Informe preços válidos (até duas casas decimais) para os tamanhos disponíveis.",
            422,
        )


class InvalidMenuPeriodError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            "invalid_menu_period",
            "A data inicial não pode ser posterior à data final.",
            422,
        )


class MenuItemNotFoundError(ApplicationError):
    def __init__(self) -> None:
        super().__init__("menu_item_not_found", "Prato não encontrado.", 404)


class InvalidMenuItemImageError(ApplicationError):
    def __init__(self, message: str = "Envie uma imagem JPEG, PNG ou WebP válida.") -> None:
        super().__init__("invalid_menu_item_image", message, 422)


class MenuItemStorageUnavailableError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            "menu_item_storage_unavailable",
            "O armazenamento de imagens está indisponível no momento.",
            503,
        )
