from app.core.exceptions import ApplicationError


class UnauthorizedError(ApplicationError):
    def __init__(self, message: str = "Credenciais inválidas.") -> None:
        super().__init__("invalid_credentials", message, 401)


class ForbiddenError(ApplicationError):
    def __init__(self) -> None:
        super().__init__("forbidden", "Você não tem permissão para esta ação.", 403)


class DuplicateAccountEmailError(Exception):
    pass


class AccountConflictError(ApplicationError):
    def __init__(self) -> None:
        super().__init__("email_already_exists", "Já existe um usuário com esse e-mail.", 409)


class InvalidAccountCompanyError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            "invalid_account_company",
            "A empresa informada não existe ou está inativa.",
            422,
        )
