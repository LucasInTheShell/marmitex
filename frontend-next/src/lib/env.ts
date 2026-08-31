/**
 * Environment configuration.
 *
 * Only deployment-level values live here. Business configuration such as the
 * order cutoff lead is persisted and managed by the admin API.
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

/** IANA timezone the cutoff and the "today" notion are evaluated in. */
export const appTimeZone = () => process.env.APP_TIME_ZONE ?? "America/Sao_Paulo";
