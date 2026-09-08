alter type payment_status add value if not exists 'review_required';

begin;
alter table order_payments add column confirmed_at timestamptz;
alter table order_payments add column last_checked_at timestamptz;
alter table order_payments add column review_reason text;
alter table order_payments drop constraint order_payments_terminal_dates_consistent;
alter table orders drop constraint orders_payment_state_consistent;
alter table orders add constraint orders_payment_state_consistent check (
  (payment_method is null and payment_status = 'not_applicable')
  or (payment_method = 'pay_on_delivery' and payment_status = 'not_applicable')
  or (payment_method = 'pix' and payment_status in (
    'pending', 'processing', 'paid', 'failed', 'expired', 'cancelled', 'refunded',
    'review_required'
  ))
);

-- Durable receipt is separate from the successfully applied event ledger.
create table payment_event_inbox (
  provider text not null,
  event_id text not null,
  payload jsonb not null,
  received_at timestamptz not null default now(),
  processed_at timestamptz,
  attempts integer not null default 0,
  next_attempt_at timestamptz not null default now(),
  last_error text,
  primary key (provider, event_id)
);
create index payment_event_inbox_pending_idx
  on payment_event_inbox (next_attempt_at) where processed_at is null;
create index order_payments_reconcile_idx
  on order_payments (provider, last_checked_at, requested_expires_at);
commit;
