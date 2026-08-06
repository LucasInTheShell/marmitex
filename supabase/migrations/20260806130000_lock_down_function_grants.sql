-- Supabase grants EXECUTE on newly created functions in `public` to `anon` by
-- default, so `revoke all ... from public` in the init migration was not enough:
-- anon kept an explicit grant and could reach create_order through
-- /rest/v1/rpc without signing in.
--
-- create_order already refuses an anonymous caller in its body (my_role() is
-- null, so it raises `forbidden`), so nothing leaked. This removes the
-- reachability as well, instead of relying only on the check inside.

revoke all on function public.my_role() from public, anon;
revoke all on function public.my_company_id() from public, anon;
revoke all on function public.is_staff() from public, anon;
revoke all on function public.create_order(
  date, uuid, text, text, text, text, text
) from public, anon;

-- RLS policy expressions are evaluated as the querying role, so `authenticated`
-- must keep EXECUTE on the helpers the policies call.
grant execute on function public.my_role() to authenticated;
grant execute on function public.my_company_id() to authenticated;
grant execute on function public.is_staff() to authenticated;
grant execute on function public.create_order(
  date, uuid, text, text, text, text, text
) to authenticated;
