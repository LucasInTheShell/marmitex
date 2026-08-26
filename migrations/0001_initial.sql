-- Mavi Connect v1 — PostgreSQL schema owned by the FastAPI application.
-- Compatible with local PostgreSQL and Supabase-managed PostgreSQL.

create extension if not exists pgcrypto;

create type account_role as enum ('company', 'kitchen', 'admin');
create type production_status as enum ('pending', 'printed', 'separated', 'delivered');
create type payment_status as enum ('not_applicable');

create table companies (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  active boolean not null default true,
  created_at timestamptz not null default now()
);

create table accounts (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  email text not null unique,
  password_hash text not null,
  company_id uuid references companies (id) on delete restrict,
  role account_role not null,
  created_at timestamptz not null default now(),
  constraint company_account_has_company check (
    (role = 'company' and company_id is not null)
    or (role in ('kitchen', 'admin') and company_id is null)
  )
);

create index accounts_company_id_idx on accounts (company_id);

create table menu_items (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  description text,
  size_options text[] not null default '{P,M,G}',
  price numeric(10, 2),
  constraint size_options_not_empty check (cardinality(size_options) > 0),
  constraint size_options_are_valid check (size_options <@ array['P','M','G']::text[]),
  constraint price_is_non_negative check (price is null or price >= 0)
);

create table menus (
  id uuid primary key default gen_random_uuid(),
  date date not null unique,
  menu_item_ids uuid[] not null default '{}',
  published boolean not null default false
);

create table orders (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null references companies (id) on delete restrict,
  date date not null,
  menu_item_id uuid not null references menu_items (id) on delete restrict,
  size text not null check (size in ('P', 'M', 'G')),
  employee_name text not null,
  employee_phone text not null,
  employee_department text not null,
  employee_cpf text not null check (employee_cpf ~ '^[0-9]{11}$'),
  production_status production_status not null default 'pending',
  payment_status payment_status not null default 'not_applicable',
  created_at timestamptz not null default now(),
  constraint one_order_per_person_per_day unique (employee_cpf, date)
);

create index orders_date_company_idx on orders (date, company_id);

create table labels_printed (
  id uuid primary key default gen_random_uuid(),
  order_id uuid not null references orders (id) on delete cascade,
  printed_at timestamptz not null default now()
);

create index labels_printed_order_id_idx on labels_printed (order_id);

create table sessions (
  id uuid primary key default gen_random_uuid(),
  account_id uuid not null references accounts (id) on delete cascade,
  token_hash char(64) not null unique,
  expires_at timestamptz not null,
  revoked_at timestamptz,
  created_at timestamptz not null default now()
);

create index sessions_active_account_idx
  on sessions (account_id, expires_at)
  where revoked_at is null;

-- Supabase is only the PostgreSQL host. Authorization lives in FastAPI;
-- browsers must never receive a database connection string or API key.

