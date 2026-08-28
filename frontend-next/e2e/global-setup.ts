/**
 * Database setup now belongs to the FastAPI/PostgreSQL stack. The suite never
 * mutates a developer database implicitly; CI should provide an isolated,
 * migrated database and create the admin account before Playwright starts.
 */
export default function globalSetup() {
  if (!process.env.E2E_DATABASE_READY) {
    throw new Error(
      "Set E2E_DATABASE_READY=1 after starting an isolated FastAPI/PostgreSQL test stack.",
    );
  }
}
