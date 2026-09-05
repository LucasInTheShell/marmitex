import hmac
import json
import logging
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any
from uuid import UUID

import httpx

from app.modules.payments.domain.entities import (
    PaymentEvent,
    PaymentPayer,
    PixPayment,
    ProviderPaymentSnapshot,
)
from app.modules.payments.domain.exceptions import (
    InvalidPaymentWebhookError,
    PaymentMethodChangeNotAllowedError,
    PaymentProviderError,
)

logger = logging.getLogger(__name__)


class AsaasPaymentGateway:
    provider = "asaas"

    def __init__(
        self,
        api_key: str,
        webhook_token: str,
        api_url: str = "https://api-sandbox.asaas.com/v3",
        timeout_seconds: float = 10.0,
        user_agent: str = "mavi-connect/0.1.0",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.api_key = api_key
        self.webhook_token = webhook_token
        self.api_url = api_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent
        self.transport = transport

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.webhook_token)

    async def find_payment(self, order_id: UUID) -> ProviderPaymentSnapshot | None:
        response = await self._request(
            "GET", "/payments", params={"externalReference": str(order_id), "limit": 2}
        )
        payments = response.get("data")
        if not isinstance(payments, list) or len(payments) > 1:
            raise PaymentProviderError()
        if not payments:
            return None
        return await self.retrieve_payment(self._required_string(payments[0], "id"))

    async def get_or_create_customer(self, payer: PaymentPayer) -> str:
        existing = await self._request(
            "GET",
            "/customers",
            params={"externalReference": payer.external_reference, "limit": 1},
        )
        customers = existing.get("data") if isinstance(existing, dict) else None
        if not isinstance(customers, list):
            raise PaymentProviderError()
        if customers:
            if not isinstance(customers[0], dict):
                raise PaymentProviderError()
            customer_id = customers[0].get("id")
            if isinstance(customer_id, str) and customer_id:
                return customer_id

        created = await self._request(
            "POST",
            "/customers",
            json_body={
                "name": payer.name,
                "cpfCnpj": self._digits(payer.tax_id),
                "email": payer.email,
                "mobilePhone": self._digits(payer.mobile_phone),
                "externalReference": payer.external_reference,
                "notificationDisabled": True,
            },
        )
        customer_id = created.get("id") if isinstance(created, dict) else None
        if not isinstance(customer_id, str) or not customer_id:
            raise PaymentProviderError()
        return customer_id

    async def create_pix_payment(
        self,
        *,
        order_id: UUID,
        customer_id: str,
        amount_cents: int,
        expires_at: datetime,
        description: str,
    ) -> PixPayment:
        external_reference = str(order_id)
        existing = await self._request(
            "GET",
            "/payments",
            params={"externalReference": external_reference, "limit": 10},
        )
        payments = existing.get("data") if isinstance(existing, dict) else None
        if not isinstance(payments, list):
            raise PaymentProviderError()
        if isinstance(payments, list):
            for candidate in payments:
                if not isinstance(candidate, dict) or candidate.get("deleted") is True:
                    continue
                if candidate.get("billingType") != "PIX":
                    continue
                self._validate_existing_payment(candidate, customer_id, amount_cents)
                payment_id = candidate.get("id")
                if isinstance(payment_id, str) and payment_id:
                    return await self._pix_instructions(
                        payment_id, str(candidate.get("status") or "PENDING")
                    )

        created = await self._request(
            "POST",
            "/lean/payments",
            json_body={
                "customer": customer_id,
                "billingType": "PIX",
                "value": amount_cents / 100,
                "dueDate": expires_at.date().isoformat(),
                "description": description,
                "externalReference": external_reference,
            },
        )
        payment_id = created.get("id") if isinstance(created, dict) else None
        if not isinstance(payment_id, str) or not payment_id:
            raise PaymentProviderError()
        return await self._pix_instructions(payment_id, str(created.get("status") or "PENDING"))

    async def retrieve_pix_payment(self, provider_payment_id: str) -> PixPayment:
        snapshot = await self.retrieve_payment(provider_payment_id)
        if snapshot.deleted or snapshot.has_refunds or snapshot.provider_status != "PENDING":
            return PixPayment(provider_payment_id, snapshot.provider_status, "", "")
        return await self._pix_instructions(snapshot.provider_payment_id, snapshot.provider_status)

    async def retrieve_payment(self, provider_payment_id: str) -> ProviderPaymentSnapshot:
        payment = await self._request("GET", f"/payments/{provider_payment_id}")
        if not isinstance(payment, dict):
            raise PaymentProviderError()
        return ProviderPaymentSnapshot(
            provider_payment_id=self._required_string(payment, "id"),
            provider_status=str(payment.get("status") or ""),
            amount_cents=self._amount_cents(payment.get("value")),
            currency="brl",
            external_reference=self._optional_string(payment.get("externalReference")),
            billing_type=str(payment.get("billingType") or ""),
            deleted=payment.get("deleted") is True,
            has_refunds=any(
                refund.get("status") not in {"CANCELLED", "DENIED"}
                for refund in (payment.get("refunds") or [])
                if isinstance(refund, dict)
            ),
        )

    async def cancel_payment(self, provider_payment_id: str) -> None:
        snapshot = await self.retrieve_payment(provider_payment_id)
        if snapshot.provider_status not in {"PENDING", "OVERDUE"} or snapshot.has_refunds:
            raise PaymentMethodChangeNotAllowedError()
        if not snapshot.deleted:
            result = await self._request("DELETE", f"/lean/payments/{provider_payment_id}")
            if result.get("deleted") is not True or result.get("id") != provider_payment_id:
                raise PaymentProviderError()
        after = await self.retrieve_payment(provider_payment_id)
        if after.provider_status not in {"PENDING", "OVERDUE"} or after.has_refunds:
            raise PaymentMethodChangeNotAllowedError()
        if not after.deleted:
            raise PaymentProviderError()

    def parse_webhook(self, payload: bytes, token: str | None) -> PaymentEvent:
        try:
            if not self.webhook_token or token is None:
                raise ValueError("Webhook token is missing")
            if not hmac.compare_digest(token, self.webhook_token):
                raise ValueError("Webhook token does not match")

            body = json.loads(payload)
            payment = body["payment"]
            if not isinstance(payment, dict):
                raise ValueError("Payment payload is invalid")
            return PaymentEvent(
                provider=self.provider,
                id=self._required_string(body, "id"),
                type=self._required_string(body, "event"),
                provider_payment_id=self._required_string(payment, "id"),
                provider_status=str(payment.get("status") or ""),
                amount_cents=self._amount_cents(payment.get("value")),
                currency="brl",
                external_reference=self._optional_string(payment.get("externalReference")),
                occurred_at=datetime.now(UTC),
            )
        except (KeyError, TypeError, ValueError, AttributeError, PaymentProviderError) as error:
            raise InvalidPaymentWebhookError() from error

    async def _pix_instructions(self, provider_payment_id: str, provider_status: str) -> PixPayment:
        if provider_status != "PENDING":
            return PixPayment(provider_payment_id, provider_status, "", "")
        qr_code = await self._request("GET", f"/payments/{provider_payment_id}/pixQrCode")
        if not isinstance(qr_code, dict):
            raise PaymentProviderError()
        return PixPayment(
            provider_payment_id=provider_payment_id,
            provider_status=provider_status,
            qr_code_base64=self._required_string(qr_code, "encodedImage"),
            copy_paste=self._required_string(qr_code, "payload"),
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        allow_not_found: bool = False,
    ) -> dict[str, Any]:
        if not self.api_key:
            raise PaymentProviderError()
        try:
            async with httpx.AsyncClient(
                base_url=self.api_url,
                headers={
                    "accept": "application/json",
                    "access_token": self.api_key,
                    "User-Agent": self.user_agent,
                },
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = await client.request(method, path, params=params, json=json_body)
            if allow_not_found and response.status_code == 404:
                return {}
            response.raise_for_status()
            result = response.json()
            if not isinstance(result, dict):
                raise ValueError("Asaas response is not an object")
            return result
        except (httpx.HTTPError, ValueError) as error:
            status_code = (
                error.response.status_code if isinstance(error, httpx.HTTPStatusError) else None
            )
            logger.warning(
                "Asaas request failed",
                extra={"method": method, "path": path, "status_code": status_code},
            )
            raise PaymentProviderError() from error

    @classmethod
    def _validate_existing_payment(
        cls, payment: dict[str, Any], customer_id: str, amount_cents: int
    ) -> None:
        if (
            payment.get("customer") != customer_id
            or cls._amount_cents(payment.get("value")) != amount_cents
        ):
            raise PaymentProviderError()

    @staticmethod
    def _amount_cents(value: Any) -> int:
        try:
            decimal_value = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except (InvalidOperation, TypeError, ValueError) as error:
            raise PaymentProviderError() from error
        if not decimal_value.is_finite() or decimal_value < 0:
            raise PaymentProviderError()
        return int(decimal_value * 100)

    @staticmethod
    def _required_string(data: dict[str, Any], key: str) -> str:
        value = data.get(key)
        if not isinstance(value, str) or not value:
            raise PaymentProviderError()
        return value

    @staticmethod
    def _optional_string(value: Any) -> str | None:
        return value if isinstance(value, str) and value else None

    @staticmethod
    def _digits(value: str) -> str:
        return "".join(character for character in value if character.isdigit())
