import { redirect } from "next/navigation";

import { ApiError, apiRequest } from "@/lib/api/client";
import { sessionToken } from "@/lib/session";
import type { Account, AccountRole } from "@/lib/types";

/** The signed-in account, or null when there is no valid session. */
export async function currentAccount(): Promise<Account | null> {
  const token = await sessionToken();
  if (!token) return null;

  try {
    return await apiRequest<Account>("/api/v1/auth/me", { token });
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) return null;
    throw error;
  }
}

/** Where each role lands after signing in. */
export function homePathFor(role: AccountRole): string {
  switch (role) {
    case "admin":
      return "/admin/empresas";
    case "company":
      return "/empresa";
    case "kitchen":
      return "/cozinha";
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
