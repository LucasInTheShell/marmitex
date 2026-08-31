-- Operational order cutoff and company-specific meal schedules.
-- Existing companies intentionally receive no assumed schedule; an admin must
-- configure the real service times before orders can be accepted for them.

begin;

create table operational_settings (
  id smallint primary key default 1 check (id = 1),
  order_cutoff_lead_minutes integer not null default 90,
  updated_at timestamptz not null default now(),
  constraint order_cutoff_lead_minutes_range
    check (order_cutoff_lead_minutes between 0 and 1440)
);

insert into operational_settings (id, order_cutoff_lead_minutes)
values (1, 90);

create table company_meal_schedules (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null references companies (id) on delete cascade,
  label text not null,
  meal_time time(0) without time zone not null,
  weekdays smallint[] not null default array[1, 2, 3, 4, 5]::smallint[],
  active boolean not null default true,
  sort_order smallint not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint company_meal_schedule_label_not_blank check (btrim(label) <> ''),
  constraint company_meal_schedule_weekdays_not_empty
    check (cardinality(weekdays) > 0),
  constraint company_meal_schedule_weekdays_valid
    check (weekdays <@ array[1, 2, 3, 4, 5, 6, 7]::smallint[]),
  constraint company_meal_schedule_sort_order_non_negative check (sort_order >= 0),
  constraint company_meal_schedule_id_company_unique unique (id, company_id)
);

create unique index company_meal_schedule_unique_label
  on company_meal_schedules (company_id, lower(btrim(label)));

create index company_meal_schedules_company_active_idx
  on company_meal_schedules (company_id, active, sort_order, meal_time);

alter table orders
  add column meal_schedule_id uuid,
  add column scheduled_for timestamptz,
  add column cutoff_at timestamptz,
  add constraint orders_meal_schedule_company_fk
    foreign key (meal_schedule_id, company_id)
    references company_meal_schedules (id, company_id)
    on delete restrict;

create index orders_meal_schedule_id_idx on orders (meal_schedule_id);

commit;
