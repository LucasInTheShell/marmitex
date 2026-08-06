-- Mavi Connect v1 — Supabase (Postgres + Auth + RLS)
--
-- Decisões que divergem do CLAUDE.md original (confirmadas com o cliente):
--   * Não existe cadastro de colaborador. O login é por EMPRESA.
--     O colaborador se identifica preenchendo nome/telefone/departamento/CPF
--     no próprio pedido.
--   * "1 marmita por pessoa por dia" (§7.2) é ancorado em CPF + data.
--   * Pedido é "cego": a conta da empresa NÃO tem SELECT em orders.
--     Inserção via função SECURITY DEFINER create_order().
--   * Corte: 10:00 do mesmo dia (valor vem de config da app, não do banco).
--
-- Fora de escopo (§4): sem pagamento, sem notificação, sem fotos, sem
-- entregador, sem multi-restaurante. payment_status existe e é fixo,
-- conforme §6/§9.

-- =====================================================================
-- Types
-- =====================================================================

create type account_role as enum ('company', 'kitchen', 'admin');
create type production_status as enum ('pending', 'printed', 'separated', 'delivered');
create type payment_status as enum ('not_applicable');

-- =====================================================================
-- Tables
-- =====================================================================

create table companies (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  active boolean not null default true,
  created_at timestamptz not null default now()
);

-- Contas de acesso. Um registro por login do Supabase Auth.
-- role = 'company' -> credencial compartilhada da empresa (company_id obrigatório)
-- role = 'kitchen' | 'admin' -> equipe da Mavi (company_id nulo)
create table accounts (
  id uuid primary key references auth.users (id) on delete cascade,
  name text not null,
  email text not null unique,
  company_id uuid references companies (id) on delete restrict,
  role account_role not null,
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
  constraint size_options_not_empty check (array_length(size_options, 1) > 0)
);

-- Um menu por data. menu_item_ids é a lista de pratos daquele dia.
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
  size text not null,

  -- Identificação do colaborador (não há cadastro na v1 — §10 confirmado).
  -- cpf armazenado só com dígitos; a app normaliza antes de gravar.
  employee_name text not null,
  employee_phone text not null,
  employee_department text not null,
  employee_cpf text not null,

  production_status production_status not null default 'pending',
  payment_status payment_status not null default 'not_applicable',
  created_at timestamptz not null default now(),

  constraint employee_cpf_is_digits check (employee_cpf ~ '^[0-9]{11}$'),
  -- §7.2: uma marmita por pessoa por dia útil
  constraint one_order_per_person_per_day unique (employee_cpf, date)
);

create index orders_date_company_idx on orders (date, company_id);

create table labels_printed (
  id uuid primary key default gen_random_uuid(),
  order_id uuid not null references orders (id) on delete cascade,
  printed_at timestamptz not null default now()
);

create index labels_printed_order_id_idx on labels_printed (order_id);

-- =====================================================================
-- Helpers — SECURITY DEFINER para não recursar a RLS de accounts
-- =====================================================================

create function my_role() returns account_role
language sql stable security definer
set search_path = public
as $$
  select role from accounts where id = auth.uid();
$$;

create function my_company_id() returns uuid
language sql stable security definer
set search_path = public
as $$
  select company_id from accounts where id = auth.uid();
$$;

create function is_staff() returns boolean
language sql stable
set search_path = public
as $$
  select my_role() in ('kitchen', 'admin');
$$;

-- =====================================================================
-- create_order — único caminho de escrita da conta da empresa.
--
-- Existe porque o pedido é "cego": a conta da empresa não pode ter SELECT
-- em orders (INSERT ... RETURNING exigiria policy de SELECT, o que
-- exporia os pedidos dos colegas pela API). A função grava e devolve
-- apenas os dados do próprio pedido recém-criado.
--
-- A validação de corte (10:00) é feita na app, que é dona do fuso e do
-- calendário de dias úteis; aqui garantimos o invariante duro: unicidade
-- por CPF/dia, empresa correta e menu publicado.
-- =====================================================================

create function create_order(
  p_date date,
  p_menu_item_id uuid,
  p_size text,
  p_employee_name text,
  p_employee_phone text,
  p_employee_department text,
  p_employee_cpf text
) returns orders
language plpgsql security definer
set search_path = public
as $$
declare
  v_company_id uuid := my_company_id();
  v_order orders;
begin
  if my_role() <> 'company' or v_company_id is null then
    raise exception 'forbidden' using errcode = '42501';
  end if;

  -- §7.4: só menu publicado, e o prato precisa estar no menu daquele dia
  if not exists (
    select 1 from menus m
    where m.date = p_date
      and m.published
      and p_menu_item_id = any (m.menu_item_ids)
  ) then
    raise exception 'menu_not_available' using errcode = 'P0001';
  end if;

  if not exists (
    select 1 from menu_items mi
    where mi.id = p_menu_item_id and p_size = any (mi.size_options)
  ) then
    raise exception 'invalid_size' using errcode = 'P0001';
  end if;

  insert into orders (
    company_id, date, menu_item_id, size,
    employee_name, employee_phone, employee_department, employee_cpf
  ) values (
    v_company_id, p_date, p_menu_item_id, p_size,
    p_employee_name, p_employee_phone, p_employee_department,
    regexp_replace(p_employee_cpf, '\D', '', 'g')
  )
  returning * into v_order;

  return v_order;
exception
  -- Não revela de quem é o pedido existente — só que aquele CPF já pediu.
  when unique_violation then
    raise exception 'already_ordered' using errcode = 'P0001';
end;
$$;

revoke all on function create_order from public;
grant execute on function create_order to authenticated;

-- =====================================================================
-- RLS
-- =====================================================================

alter table companies enable row level security;
alter table accounts enable row level security;
alter table menu_items enable row level security;
alter table menus enable row level security;
alter table orders enable row level security;
alter table labels_printed enable row level security;

-- companies: a empresa vê só a si mesma; cozinha/admin veem todas
create policy companies_select on companies for select to authenticated
  using (is_staff() or id = my_company_id());

create policy companies_admin_all on companies for all to authenticated
  using (my_role() = 'admin') with check (my_role() = 'admin');

-- accounts: cada conta vê a si mesma; admin gerencia todas.
-- A cozinha não precisa ler accounts (o nome do colaborador vive em orders).
create policy accounts_select_self on accounts for select to authenticated
  using (id = auth.uid() or my_role() = 'admin');

create policy accounts_admin_all on accounts for all to authenticated
  using (my_role() = 'admin') with check (my_role() = 'admin');

-- menu_items: legível por qualquer autenticado; escrita só admin
create policy menu_items_select on menu_items for select to authenticated
  using (true);

create policy menu_items_admin_all on menu_items for all to authenticated
  using (my_role() = 'admin') with check (my_role() = 'admin');

-- menus: §7.4 — a empresa só enxerga published = true
create policy menus_select on menus for select to authenticated
  using (is_staff() or published);

create policy menus_admin_all on menus for all to authenticated
  using (my_role() = 'admin') with check (my_role() = 'admin');

-- orders: SELECT só para cozinha/admin. A conta da empresa NÃO lê pedidos
-- (pedido cego) e NÃO escreve direto — usa create_order().
create policy orders_staff_select on orders for select to authenticated
  using (is_staff());

create policy orders_staff_update on orders for update to authenticated
  using (is_staff()) with check (is_staff());

create policy orders_admin_delete on orders for delete to authenticated
  using (my_role() = 'admin');

-- labels_printed: cozinha e admin imprimem (confirmado com o cliente)
create policy labels_staff_select on labels_printed for select to authenticated
  using (is_staff());

create policy labels_staff_insert on labels_printed for insert to authenticated
  with check (is_staff());
