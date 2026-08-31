from app.core.exceptions import ApplicationError


class EmptyMenuError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            "empty_menu", "Nenhum cardápio preenchido foi encontrado.", 422
        )


class InvalidMenuPeriodError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            "invalid_menu_period",
            "A data inicial não pode ser posterior à data final.",
            422,
        )

