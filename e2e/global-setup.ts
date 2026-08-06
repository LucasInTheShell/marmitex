import { execSync } from "node:child_process";

/**
 * Resets the local Supabase database so every run starts from the migrations
 * plus supabase/seed.sql (which creates the admin credential).
 *
 * Set E2E_SKIP_DB_RESET=1 when pointing the suite at a database you reset
 * yourself.
 */
export default function globalSetup() {
  if (process.env.E2E_SKIP_DB_RESET === "1") return;

  execSync("npx supabase db reset", { stdio: "inherit" });
}
