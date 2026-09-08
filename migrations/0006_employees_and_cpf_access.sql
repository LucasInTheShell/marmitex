-- Employees are operational identities, not authenticated accounts.
-- A short-lived opaque session is issued after a CPF matches an active employee.

begin;

create table employees (
  id uuid primary key default gen_random_uuid(),
  company_id uuid not null references companies (id) on delete restrict,
  name text not null,
  cpf char(11) not null unique,
  phone text not null,
  department text not null,
  internal_id text,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint employees_name_not_blank check (btrim(name) <> ''),
  constraint employees_cpf_digits check (cpf ~ '^[0-9]{11}$'),
  constraint employees_phone_digits check (phone ~ '^[0-9]{10,15}$'),
  constraint employees_department_not_blank check (btrim(department) <> ''),
  constraint employees_internal_id_not_blank
    check (internal_id is null or btrim(internal_id) <> '')
);

create index employees_company_name_idx on employees (company_id, name);
create index employees_company_active_idx on employees (company_id, active);

create table employee_sessions (
  id uuid primary key default gen_random_uuid(),
  employee_id uuid not null references employees (id) on delete cascade,
  token_hash char(64) not null unique,
  expires_at timestamptz not null,
  revoked_at timestamptz,
  created_at timestamptz not null default now()
);

create index employee_sessions_active_employee_idx
  on employee_sessions (employee_id, expires_at)
  where revoked_at is null;

-- Preserve people already present in historical orders. If the same CPF appears
-- in more than one company, the most recent order defines the initial company.
insert into employees (
  company_id,
  name,
  cpf,
  phone,
  department,
  internal_id,
  created_at,
  updated_at
)
select distinct on (employee_cpf)
  company_id,
  employee_name,
  employee_cpf,
  regexp_replace(employee_phone, '[^0-9]', '', 'g'),
  employee_department,
  employee_internal_id,
  created_at,
  updated_at
from orders
where employee_cpf ~ '^[0-9]{11}$'
  and length(regexp_replace(employee_phone, '[^0-9]', '', 'g')) between 10 and 15
order by employee_cpf, created_at desc, id desc;

commit;
