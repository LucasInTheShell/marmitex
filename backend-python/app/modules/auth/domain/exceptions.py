from app.core.exceptions import ApplicationError


class UnauthorizedError(ApplicationError):
    def __init__(self, message: str = "Credenciais inválidas.") -> None:
        super().__init__("invalid_credentials", message, 401)


class ForbiddenError(ApplicationError):
    def __init__(self) -> None:
        super().__init__("forbidden", "Você não tem permissão para esta ação.", 403)

