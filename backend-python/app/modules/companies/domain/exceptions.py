from app.core.exceptions import ApplicationError


class CompanyConflictError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            "email_already_exists", "Já existe um acesso com esse e-mail.", 409
        )


class DuplicateCompanyEmailError(Exception):
    pass


class CompanyNotFoundError(ApplicationError):
    def __init__(self) -> None:
        super().__init__("company_not_found", "Empresa não encontrada.", 404)


class MealScheduleNotFoundError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            "meal_schedule_not_found", "Horário de refeição não encontrado.", 404
        )


class MealScheduleConflictError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            "meal_schedule_already_exists",
            "Já existe um horário com esse nome para a empresa.",
            409,
        )


class DuplicateMealScheduleError(Exception):
    pass


class MealScheduleLimitError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            "meal_schedule_limit_reached",
            "Cada empresa pode possuir no máximo oito horários de refeição.",
            422,
        )

