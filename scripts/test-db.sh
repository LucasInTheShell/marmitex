#!/usr/bin/env bash
#
# Applies the migrations to a throwaway database and runs the RLS suite.
# Uses a plain Postgres server plus a small Supabase shim (supabase/tests/shim.sql),
# so it does not need the Supabase container stack.
#
# Requires psql and a reachable Postgres superuser connection. Override with:
#   PGHOST, PGPORT, PGUSER  (defaults: local socket, current user)

set -euo pipefail

DB_NAME="${TEST_DB_NAME:-mavi_connect_test}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

psql -v ON_ERROR_STOP=1 -q -d postgres \
  -c "drop database if exists ${DB_NAME} with (force);" \
  -c "create database ${DB_NAME};"

run() {
  psql -v ON_ERROR_STOP=1 -q -d "${DB_NAME}" -f "$1"
}

run "${ROOT_DIR}/supabase/tests/shim.sql"

for migration in "${ROOT_DIR}"/supabase/migrations/*.sql; do
  run "${migration}"
done

run "${ROOT_DIR}/supabase/tests/grants.sql"
run "${ROOT_DIR}/supabase/tests/rls.sql"

psql -v ON_ERROR_STOP=1 -q -d postgres \
  -c "drop database if exists ${DB_NAME} with (force);"
