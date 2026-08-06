import "server-only";

import { createClient } from "@supabase/supabase-js";

import { supabaseServiceRoleKey, supabaseUrl } from "@/lib/env";

/**
 * Service-role client. Bypasses RLS, so it is only used for things the Auth API
 * requires elevated rights for: creating the credential of a company or of a
 * staff member. Never expose it to the browser.
 */
export function createAdminClient() {
  return createClient(supabaseUrl(), supabaseServiceRoleKey(), {
    auth: { autoRefreshToken: false, persistSession: false },
  });
}
