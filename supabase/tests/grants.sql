-- TEST-ONLY. Supabase grants table privileges to the API roles automatically;
-- a plain Postgres server does not. Applied after the migration so RLS is what
-- decides access in the tests, not missing GRANTs.

grant select, insert, update, delete on all tables in schema public
  to anon, authenticated, service_role;

grant usage, select on all sequences in schema public
  to anon, authenticated, service_role;
