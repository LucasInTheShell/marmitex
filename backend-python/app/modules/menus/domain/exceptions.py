from app.core.exceptions import ApplicationError


class EmptyMenuError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            "empty_menu", "Nenhum cardápio preenchido foi encontrado.", 422
        )

