/**
 * Environment configuration.
 *
 * Business values that the client may still change (cutoff time) live here as
 * env vars — never hardcoded in feature code. See CLAUDE.md §7.
 */

function required(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing environment variable: ${name}`);
  }
  return value;
}

/** Server-only API origin. It is intentionally not exposed to browser code. */
export const apiUrl = () => required("API_URL").replace(/\/$/, "");

/** Time of day, same day, after which orders for that day are closed. */
export const orderCutoffTime = () => process.env.ORDER_CUTOFF_TIME ?? "10:00";

/** IANA timezone the cutoff and the "today" notion are evaluated in. */
export const appTimeZone = () => process.env.APP_TIME_ZONE ?? "America/Sao_Paulo";
