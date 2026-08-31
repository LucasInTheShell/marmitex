from app.core.exceptions import ApplicationError


class InvalidCutoffLeadError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            "invalid_cutoff_lead",
            "A antecedência deve estar entre 0 e 1440 minutos.",
            422,
        )
