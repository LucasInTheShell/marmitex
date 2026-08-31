from app.core.exceptions import ApplicationError


class OrderDomainError(ApplicationError):
    pass


class CompanyCannotOrderError(OrderDomainError):
    def __init__(self) -> None:
        super().__init__(
            "company_cannot_order",
            "A empresa não existe, está inativa ou não possui acesso a pedidos.",
            422,
        )


class InvalidMealScheduleError(OrderDomainError):
    def __init__(self) -> None:
        super().__init__(
            "invalid_meal_schedule",
            "O horário selecionado não está disponível para esta empresa e data.",
            422,
        )


class OrderingWindowClosedError(OrderDomainError):
    def __init__(self) -> None:
        super().__init__(
            "ordering_window_closed",
            "O horário limite para este pedido já foi atingido.",
            409,
        )


class MenuUnavailableError(OrderDomainError):
    def __init__(self) -> None:
        super().__init__(
            "menu_unavailable",
            "Não existe cardápio publicado e disponível para a data informada.",
            422,
        )


class MenuItemUnavailableError(OrderDomainError):
    def __init__(self) -> None:
        super().__init__(
            "menu_item_unavailable",
            "Um ou mais pratos não pertencem ao cardápio publicado da data.",
            422,
        )


class MenuItemWithoutPriceError(OrderDomainError):
    def __init__(self) -> None:
        super().__init__(
            "menu_item_without_price",
            "Todos os pratos do pedido precisam possuir preço cadastrado.",
            422,
        )


class InvalidOrderSizeError(OrderDomainError):
    def __init__(self) -> None:
        super().__init__(
            "invalid_order_size",
            "O tamanho escolhido não está disponível para um dos pratos.",
            422,
        )


class InvalidOrderItemsError(OrderDomainError):
    def __init__(self, message: str = "Revise os itens e quantidades do pedido.") -> None:
        super().__init__("invalid_order_items", message, 422)


class InvalidEmployeeCpfError(OrderDomainError):
    def __init__(self) -> None:
        super().__init__("invalid_employee_cpf", "Informe um CPF com 11 dígitos.", 422)


class InvalidEmployeePhoneError(OrderDomainError):
    def __init__(self) -> None:
        super().__init__("invalid_employee_phone", "Informe um telefone válido.", 422)


class InvalidEmployeeDataError(OrderDomainError):
    def __init__(self) -> None:
        super().__init__(
            "invalid_employee_data",
            "Nome e setor do funcionário são obrigatórios.",
            422,
        )


class OrderAlreadyExistsError(OrderDomainError):
    def __init__(self) -> None:
        super().__init__(
            "order_already_exists",
            "Este funcionário já possui um pedido nesta empresa e data.",
            409,
        )


class IdempotencyConflictError(OrderDomainError):
    def __init__(self) -> None:
        super().__init__(
            "idempotency_conflict",
            "Esta chave de idempotência já foi usada com outro pedido.",
            409,
        )


class OrderNotFoundError(OrderDomainError):
    def __init__(self) -> None:
        super().__init__("order_not_found", "Pedido não encontrado.", 404)


class InvalidOrderPeriodError(OrderDomainError):
    def __init__(self) -> None:
        super().__init__(
            "invalid_order_period",
            "O período deve estar em ordem e possuir no máximo 31 dias.",
            422,
        )


class OrderCannotBeCancelledError(OrderDomainError):
    def __init__(self) -> None:
        super().__init__(
            "order_cannot_be_cancelled",
            "Somente pedidos pendentes e dentro do prazo podem ser cancelados.",
            409,
        )


class InvalidProductionStatusTransitionError(OrderDomainError):
    def __init__(self) -> None:
        super().__init__(
            "invalid_production_status_transition",
            "A mudança de status solicitada não é permitida.",
            409,
        )
