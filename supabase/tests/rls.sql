-- Verifies the RLS rules of CLAUDE.md §6 and §7 against a real Postgres server.
-- Runs with ON_ERROR_STOP, so a failed assertion fails the whole run.

-- A null condition is a failure, not a pass: it usually means RLS filtered the
-- row the assertion was reading, which is exactly the bug worth catching.
create or replace function assert_true(condition boolean, message text)
returns void language plpgsql as $$
begin
  if condition is null then
    raise exception 'ASSERTION INCONCLUSIVE (null condition): %', message;
  end if;
  if not condition then
    raise exception 'ASSERTION FAILED: %', message;
  end if;
end;
$$;

/*
 * The three helpers below impersonate an account the way PostgREST does:
 * the JWT `sub` claim goes into request.jwt.claims and the connection switches
 * to the `authenticated` role, which is the role RLS is written against.
 *
 * The role comes from the function's own SET clause rather than a `SET LOCAL`
 * statement in the body. SET LOCAL would last until the end of the transaction,
 * so when the whole suite runs inside one transaction the `authenticated` role
 * would leak into the assertions that follow and silently read nothing. A SET
 * clause is reverted when the function returns, on the exception path too.
 */

create or replace function count_as(account_id uuid, query text)
returns bigint language plpgsql
set role = authenticated
as $$
declare
  result bigint;
begin
  perform set_config('request.jwt.claims',
    json_build_object('sub', account_id)::text, true);
  execute query into result;
  return result;
end;
$$;

create or replace function run_as(account_id uuid, statement text)
returns void language plpgsql
set role = authenticated
as $$
begin
  perform set_config('request.jwt.claims',
    json_build_object('sub', account_id)::text, true);
  execute statement;
end;
$$;

create or replace function expect_error(
  account_id uuid,
  statement text,
  expected_sqlstate text,
  expected_message text default null
) returns void language plpgsql
set role = authenticated
as $$
begin
  begin
    perform set_config('request.jwt.claims',
      json_build_object('sub', account_id)::text, true);
    execute statement;
  exception
    when others then
      if sqlstate <> expected_sqlstate then
        raise exception 'ASSERTION FAILED: expected sqlstate %, got % (%)',
          expected_sqlstate, sqlstate, sqlerrm;
      end if;
      if expected_message is not null and sqlerrm <> expected_message then
        raise exception 'ASSERTION FAILED: expected "%", got "%"',
          expected_message, sqlerrm;
      end if;
      return;
  end;

  raise exception 'ASSERTION FAILED: statement was expected to fail: %', statement;
end;
$$;

-- Signed-out callers must not be able to reach create_order through the API at
-- all. The function also refuses them in its body, but Supabase grants EXECUTE
-- to `anon` by default, so the grant has to be revoked explicitly.
create or replace function expect_anon_denied()
returns void language plpgsql
set role = anon
as $$
begin
  begin
    execute $q$
      select create_order('2026-08-03', '00000000-0000-0000-0000-0000000000d1',
        'M', 'Anon', '11900000000', 'TI', '11144477735')
    $q$;
  exception
    when insufficient_privilege then return;
  end;
  raise exception 'ASSERTION FAILED: anon must not be able to execute create_order';
end;
$$;

-- =====================================================================
-- Fixtures
-- =====================================================================

insert into auth.users (id, email) values
  ('00000000-0000-0000-0000-0000000000a1', 'admin@mavi.local'),
  ('00000000-0000-0000-0000-0000000000b1', 'cozinha@mavi.local'),
  ('00000000-0000-0000-0000-0000000000c1', 'acme@empresa.local'),
  ('00000000-0000-0000-0000-0000000000c2', 'globex@empresa.local');

insert into companies (id, name) values
  ('00000000-0000-0000-0000-00000000aa00', 'Acme'),
  ('00000000-0000-0000-0000-00000000bb00', 'Globex');

insert into accounts (id, name, email, company_id, role) values
  ('00000000-0000-0000-0000-0000000000a1', 'Admin', 'admin@mavi.local', null, 'admin'),
  ('00000000-0000-0000-0000-0000000000b1', 'Cozinha', 'cozinha@mavi.local', null, 'kitchen'),
  ('00000000-0000-0000-0000-0000000000c1', 'Acme', 'acme@empresa.local',
   '00000000-0000-0000-0000-00000000aa00', 'company'),
  ('00000000-0000-0000-0000-0000000000c2', 'Globex', 'globex@empresa.local',
   '00000000-0000-0000-0000-00000000bb00', 'company');

insert into menu_items (id, name, size_options) values
  ('00000000-0000-0000-0000-0000000000d1', 'Frango grelhado', '{P,M,G}'),
  ('00000000-0000-0000-0000-0000000000d2', 'Feijoada', '{M,G}');

insert into menus (date, menu_item_ids, published) values
  ('2026-08-03',
   '{00000000-0000-0000-0000-0000000000d1,00000000-0000-0000-0000-0000000000d2}', true),
  ('2026-08-04', '{00000000-0000-0000-0000-0000000000d1}', false),
  ('2026-08-05', '{00000000-0000-0000-0000-0000000000d1}', true);

-- =====================================================================
-- §7.4 — a company only sees published menus
-- =====================================================================

select assert_true(
  count_as('00000000-0000-0000-0000-0000000000c1', 'select count(*) from menus') = 2,
  'company must only see published menus'
);

select expect_anon_denied();

-- Guards the harness itself: if a helper left the connection as `authenticated`,
-- every assertion after it would read through RLS and pass on empty results.
select assert_true(
  current_user <> 'authenticated',
  'helpers must not leak the authenticated role into the rest of the suite'
);

select assert_true(
  count_as('00000000-0000-0000-0000-0000000000b1', 'select count(*) from menus') = 3,
  'kitchen must see every menu, published or not'
);

select assert_true(
  count_as('00000000-0000-0000-0000-0000000000a1', 'select count(*) from menus') = 3,
  'admin must see every menu, published or not'
);

-- =====================================================================
-- §7.5 — a company only sees itself
-- =====================================================================

select assert_true(
  count_as('00000000-0000-0000-0000-0000000000c1', 'select count(*) from companies') = 1,
  'company must only see its own company row'
);

select assert_true(
  count_as('00000000-0000-0000-0000-0000000000b1', 'select count(*) from companies') = 2,
  'kitchen must see every company'
);

-- =====================================================================
-- create_order — the only write path a company has
-- =====================================================================

select run_as('00000000-0000-0000-0000-0000000000c1', $$
  select create_order('2026-08-03', '00000000-0000-0000-0000-0000000000d1', 'M',
    'Maria Souza', '11999998888', 'Financeiro', '390.533.447-05')
$$);

select assert_true(
  (select company_id from orders where employee_name = 'Maria Souza')
    = '00000000-0000-0000-0000-00000000aa00',
  'create_order must attach the order to the company of the signed-in account'
);

select assert_true(
  (select employee_cpf from orders where employee_name = 'Maria Souza') = '39053344705',
  'create_order must normalise the CPF to digits'
);

-- §7.2 — the same CPF cannot order twice on the same day
select expect_error('00000000-0000-0000-0000-0000000000c1', $$
  select create_order('2026-08-03', '00000000-0000-0000-0000-0000000000d2', 'G',
    'Maria S.', '11999998888', 'Financeiro', '39053344705')
$$, 'P0001', 'already_ordered');

-- …but may order on another published day
select run_as('00000000-0000-0000-0000-0000000000c1', $$
  select create_order('2026-08-05', '00000000-0000-0000-0000-0000000000d1', 'P',
    'Maria Souza', '11999998888', 'Financeiro', '39053344705')
$$);

select assert_true(
  (select count(*) from orders where employee_cpf = '39053344705') = 2,
  'the same person must be able to order on two different days'
);

-- §7.4 — an unpublished day cannot be ordered
select expect_error('00000000-0000-0000-0000-0000000000c1', $$
  select create_order('2026-08-04', '00000000-0000-0000-0000-0000000000d1', 'M',
    'Joao Lima', '11988887777', 'TI', '11144477735')
$$, 'P0001', 'menu_not_available');

-- A day with no menu at all cannot be ordered
select expect_error('00000000-0000-0000-0000-0000000000c1', $$
  select create_order('2026-08-06', '00000000-0000-0000-0000-0000000000d1', 'M',
    'Joao Lima', '11988887777', 'TI', '11144477735')
$$, 'P0001', 'menu_not_available');

-- A size the dish does not offer is refused
select expect_error('00000000-0000-0000-0000-0000000000c1', $$
  select create_order('2026-08-03', '00000000-0000-0000-0000-0000000000d2', 'P',
    'Joao Lima', '11988887777', 'TI', '11144477735')
$$, 'P0001', 'invalid_size');

-- The kitchen is not an ordering channel
select expect_error('00000000-0000-0000-0000-0000000000b1', $$
  select create_order('2026-08-03', '00000000-0000-0000-0000-0000000000d1', 'M',
    'Fulano', '11900000000', 'Cozinha', '11144477735')
$$, '42501');

-- =====================================================================
-- §6 — the order is blind: a company cannot read orders at all
-- =====================================================================

select assert_true(
  count_as('00000000-0000-0000-0000-0000000000c1', 'select count(*) from orders') = 0,
  'company must not read orders, not even its own'
);

select assert_true(
  count_as('00000000-0000-0000-0000-0000000000c2', 'select count(*) from orders') = 0,
  'company must not read another company orders'
);

select assert_true(
  count_as('00000000-0000-0000-0000-0000000000b1', 'select count(*) from orders') = 2,
  'kitchen must read every order'
);

select assert_true(
  count_as('00000000-0000-0000-0000-0000000000a1', 'select count(*) from orders') = 2,
  'admin must read every order'
);

-- A company cannot write to orders directly either
select expect_error('00000000-0000-0000-0000-0000000000c1', $$
  insert into orders (company_id, date, menu_item_id, size,
    employee_name, employee_phone, employee_department, employee_cpf)
  values ('00000000-0000-0000-0000-00000000aa00', '2026-08-03',
    '00000000-0000-0000-0000-0000000000d1', 'M',
    'Bypass', '11900000000', 'TI', '11144477735')
$$, '42501');

-- =====================================================================
-- Accounts are not browsable by a company
-- =====================================================================

select assert_true(
  count_as('00000000-0000-0000-0000-0000000000c1', 'select count(*) from accounts') = 1,
  'company must only see its own account row'
);

select assert_true(
  count_as('00000000-0000-0000-0000-0000000000a1', 'select count(*) from accounts') = 4,
  'admin must see every account'
);

-- =====================================================================
-- §6 — payment_status exists from day one and stays separate
-- =====================================================================

select assert_true(
  (select count(*) from orders where payment_status = 'not_applicable') = 2,
  'orders must be created with payment_status = not_applicable'
);

select assert_true(
  (select count(*) from orders where production_status = 'pending') = 2,
  'orders must be created with production_status = pending'
);

\echo 'RLS suite passed'
