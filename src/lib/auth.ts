import { redirect } from "next/navigation";

import { createClient } from "@/lib/supabase/server";
import type { Account, AccountRole } from "@/lib/types";

/** The signed-in account, or null when there is no valid session. */
export async function currentAccount(): Promise<Account | null> {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) return null;

  const { data } = await supabase
    .from("accounts")
    .select("id, name, email, company_id, role")
    .eq("id", user.id)
    .single();

  return data ?? null;
}

/** Where each role lands after signing in. */
export function homePathFor(role: AccountRole): string {
  switch (role) {
    case "admin":
      return "/admin/empresas";
    default:
      return "/login";
  }
}

/**
 * Guards a page. Redirects to the login screen when signed out, and to the
 * account's own area when it has the wrong role.
 */
export async function requireRole(role: AccountRole): Promise<Account> {
  const account = await currentAccount();

  if (!account) redirect("/login");
  if (account.role !== role) redirect(homePathFor(account.role));

  return account;
}
