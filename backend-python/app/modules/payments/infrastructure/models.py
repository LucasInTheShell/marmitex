from app.modules.payments.domain.entities import OrderPayment


def payment_from_row(row: dict) -> OrderPayment:
    return OrderPayment(
        id=row["id"],
        order_id=row["order_id"],
        provider=row["provider"],
        provider_payment_id=row["provider_payment_id"],
        provider_status=row["provider_status"],
        amount_cents=row["amount_cents"],
        currency=row["currency"],
        requested_expires_at=row["requested_expires_at"],
        paid_at=row["paid_at"],
        failed_at=row["failed_at"],
        cancelled_at=row["cancelled_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        confirmed_at=row.get("confirmed_at"),
    )
