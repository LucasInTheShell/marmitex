-- Generalize the payment persistence and add Asaas as the active Pix provider.

alter type payment_provider add value if not exists 'asaas';

begin;

alter table order_payments
  rename column provider_payment_intent_id to provider_payment_id;

alter table stripe_webhook_events
  rename to payment_webhook_events;

alter table payment_webhook_events
  rename column stripe_event_id to provider_event_id;

alter table payment_webhook_events
  rename column provider_payment_intent_id to provider_payment_id;

alter table payment_webhook_events
  add column provider payment_provider;

update payment_webhook_events
set provider = 'stripe'
where provider is null;

alter table payment_webhook_events
  alter column provider set not null;

alter table payment_webhook_events
  drop constraint stripe_webhook_events_pkey;

alter table payment_webhook_events
  add primary key (provider, provider_event_id);

create index payment_webhook_events_payment_idx
  on payment_webhook_events (provider, provider_payment_id);

create table payment_customers (
  id uuid primary key default gen_random_uuid(),
  provider payment_provider not null,
  company_id uuid not null references companies (id) on delete restrict,
  employee_cpf char(11) not null,
  provider_customer_id text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint payment_customers_cpf_digits check (employee_cpf ~ '^[0-9]{11}$'),
  constraint payment_customers_identity_unique
    unique (provider, company_id, employee_cpf),
  constraint payment_customers_provider_id_unique
    unique (provider, provider_customer_id)
);

create index payment_customers_company_idx
  on payment_customers (company_id, provider);

commit;
