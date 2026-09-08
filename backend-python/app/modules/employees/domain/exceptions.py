from app.core.exceptions import ApplicationError


class EmployeeNotFoundError(ApplicationError):
    def __init__(self) -> None:
        super().__init__("employee_not_found", "Funcionário não encontrado.", 404)


class EmployeeCpfConflictError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            "employee_cpf_already_exists",
            "Este CPF já está vinculado a um funcionário.",
            409,
        )


class InvalidEmployeeError(ApplicationError):
    def __init__(self, message: str = "Revise os dados do funcionário.") -> None:
        super().__init__("invalid_employee", message, 422)


class EmployeeAccessDeniedError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            "invalid_employee_access",
            "CPF não cadastrado ou acesso indisponível.",
            401,
        )
