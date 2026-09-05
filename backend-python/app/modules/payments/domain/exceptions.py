from app.core.exceptions import ApplicationError


class PaymentError(ApplicationError):
    pass


class PaymentNotFoundError(PaymentError):
    def __init__(self) -> None:
        super().__init__("payment_not_found", "Pagamento não encontrado.", 404)


class PixUnavailableError(PaymentError):
    def __init__(self, message: str = "O Pix não está disponível para este pedido.") -> None:
        super().__init__("pix_unavailable", message, 409)


class PaymentMethodChangeNotAllowedError(PaymentError):
    def __init__(self) -> None:
        super().__init__(
            "payment_method_change_not_allowed",
            "A forma de pagamento não pode mais ser alterada.",
            409,
        )


class PaymentProviderError(PaymentError):
    def __init__(self) -> None:
        super().__init__(
            "payment_provider_unavailable",
            "Não foi possível iniciar o Pix agora. Tente novamente.",
            503,
        )


class InvalidPaymentWebhookError(PaymentError):
    def __init__(self) -> None:
        super().__init__("invalid_payment_webhook", "Webhook de pagamento inválido.", 400)


class PaymentReconciliationError(PaymentError):
    def __init__(self) -> None:
        super().__init__(
            "payment_reconciliation_failed",
            "O pagamento recebido não corresponde ao pedido.",
            409,
        )
