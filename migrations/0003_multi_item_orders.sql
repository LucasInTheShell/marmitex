-- Multi-item orders and operational lifecycle.
-- Existing single-item orders are migrated to one row in order_items.

alter type production_status add value if not exists 'cancelled';

begin;

alter table orders
  drop constraint if exists one_order_per_person_per_day;

alter table orders
  add column order_number bigint generated always as identity,
  add column meal_schedule_label text,
  add column employee_internal_id text,
  add column total_price numeric(12, 2) not null default 0,
  add column idempotency_key text,
  add column request_fingerprint char(64),
  add column updated_at timestamptz not null default now(),
  add column cancelled_at timestamptz,
  add column cancelled_by_account_id uuid references accounts (id) on delete restrict,
  add column cancellation_reason text,
  add constraint orders_order_number_unique unique (order_number),
  add constraint orders_employee_name_not_blank check (btrim(employee_name) <> ''),
  add constraint orders_employee_department_not_blank
    check (btrim(employee_department) <> ''),
  add constraint orders_employee_internal_id_not_blank
    check (employee_internal_id is null or btrim(employee_internal_id) <> ''),
  add constraint orders_total_price_non_negative check (total_price >= 0),
  add constraint orders_idempotency_key_length
    check (idempotency_key is null or char_length(idempotency_key) between 1 and 120),
  add constraint orders_request_fingerprint_with_key check (
    (idempotency_key is null and request_fingerprint is null)
    or (idempotency_key is not null and request_fingerprint is not null)
  ),
  add constraint orders_cancellation_fields_consistent check (
    (production_status = 'cancelled' and cancelled_at is not null)
    or (production_status <> 'cancelled' and cancelled_at is null)
  );

update orders o
set meal_schedule_label = schedule.label
from company_meal_schedules schedule
where schedule.id = o.meal_schedule_id;

create table order_items (
  id uuid primary key default gen_random_uuid(),
  order_id uuid not null references orders (id) on delete cascade,
  position smallint not null,
  menu_item_id uuid not null references menu_items (id) on delete restrict,
  item_name text not null,
  item_description text,
  size text not null check (size in ('P', 'M', 'G')),
  quantity smallint not null check (quantity between 1 and 10),
  unit_price numeric(10, 2) not null check (unit_price >= 0),
  subtotal numeric(12, 2) not null check (subtotal >= 0),
  notes text,
  constraint order_items_position_non_negative check (position >= 0),
  constraint order_items_name_not_blank check (btrim(item_name) <> ''),
  constraint order_items_notes_length
    check (notes is null or char_length(notes) <= 300),
  constraint order_items_subtotal_matches
    check (subtotal = unit_price * quantity),
  constraint order_items_order_position_unique unique (order_id, position),
  constraint order_items_order_item_size_unique unique (order_id, menu_item_id, size)
);

insert into order_items (
  order_id,
  position,
  menu_item_id,
  item_name,
  item_description,
  size,
  quantity,
  unit_price,
  subtotal
)
select
  o.id,
  0,
  item.id,
  item.name,
  item.description,
  o.size,
  1,
  coalesce(item.price, 0),
  coalesce(item.price, 0)
from orders o
join menu_items item on item.id = o.menu_item_id;

update orders o
set total_price = totals.total_price
from (
  select order_id, sum(subtotal) as total_price
  from order_items
  group by order_id
) totals
where totals.order_id = o.id;

alter table orders
  drop column menu_item_id,
  drop column size;

alter table orders
  add constraint one_order_per_company_person_day
    unique (company_id, employee_cpf, date),
  add constraint orders_company_idempotency_unique
    unique (company_id, idempotency_key);

create index orders_date_status_idx
  on orders (date, production_status, created_at);

create index orders_company_date_status_idx
  on orders (company_id, date, production_status, created_at);

create index order_items_order_id_idx
  on order_items (order_id, position);

commit;
