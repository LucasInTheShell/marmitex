-- TEST-ONLY. Recreates the pieces of Supabase that the migration depends on
-- (auth schema, auth.uid(), the anon/authenticated/service_role roles) so the
-- schema and its RLS policies can be verified against a plain Postgres server.
--
-- Never run this against a real Supabase database — Supabase already provides
-- all of it.

do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'anon') then
    create role anon nologin noinherit;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'authenticated') then
    create role authenticated nologin noinherit;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'service_role') then
    create role service_role nologin noinherit bypassrls;
  end if;
end
$$;

create extension if not exists pgcrypto;

create schema if not exists auth;

create table if not exists auth.users (
  id uuid primary key,
  email text unique
);

-- Supabase exposes the JWT claims of the current request through this GUC.
create or replace function auth.uid() returns uuid
language sql stable
as $$
  select nullif(
    current_setting('request.jwt.claims', true)::json ->> 'sub',
    ''
  )::uuid;
$$;

grant usage on schema public, auth to anon, authenticated, service_role;
grant select on auth.users to anon, authenticated, service_role;
