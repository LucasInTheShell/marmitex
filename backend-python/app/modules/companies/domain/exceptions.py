from app.core.exceptions import ApplicationError


class CompanyConflictError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            "email_already_exists", "Já existe um acesso com esse e-mail.", 409
        )


class DuplicateCompanyEmailError(Exception):
    pass

