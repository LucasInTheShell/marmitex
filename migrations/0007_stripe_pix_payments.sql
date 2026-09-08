-- Stripe Pix payments while keeping payment and production lifecycles separate.

alter type payment_status add value if not exists 'pending';
alter type payment_status add value if not exists 'processing';
alter type payment_status add value if not exists 'paid';
alter type payment_status add value if not exists 'failed';
alter type payment_status add value if not exists 'expired';
alter type payment_status add value if not exists 'cancelled';
alter type payment_status add value if not exists 'refunded';

create type payment_method as enum ('pay_on_delivery', 'pix');
create type payment_provider as enum ('stripe');

begin;

alter table orders
  add column payment_method payment_method;

create table order_payments (
  id uuid primary key default gen_random_uuid(),
  order_id uuid not null unique references orders (id) on delete restrict,
  provider payment_provider not null,
  provider_payment_intent_id text not null unique,
  provider_status text not null,
  amount_cents bigint not null check (amount_cents >= 50),
  currency char(3) not null default 'brl' check (currency = lower(currency)),
  requested_expires_at timestamptz not null,
  paid_at timestamptz,
  failed_at timestamptz,
  cancelled_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint order_payments_terminal_dates_consistent check (
    num_nonnulls(paid_at, failed_at, cancelled_at) <= 1
  )
);

create index order_payments_order_id_idx on order_payments (order_id);
create index order_payments_provider_status_idx
  on order_payments (provider, provider_status);

create table stripe_webhook_events (
  stripe_event_id text primary key,
  event_type text not null,
  provider_payment_intent_id text,
  processed_at timestamptz not null default now()
);

alter table orders
  add constraint orders_payment_state_consistent check (
    (payment_method is null and payment_status = 'not_applicable')
    or (payment_method = 'pay_on_delivery' and payment_status = 'not_applicable')
    or (
      payment_method = 'pix'
      and payment_status in (
        'pending', 'processing', 'paid', 'failed', 'expired',
        'cancelled', 'refunded'
      )
    )
  );

create index orders_company_date_payment_idx
  on orders (company_id, date, payment_method, payment_status);

commit;
