#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

docker compose up -d support-db

echo "Waiting for Supabase support-db..."
for _ in $(seq 1 60); do
  if docker compose exec -T -e PGPASSWORD=postgres support-db \
    psql -U supabase_admin -d postgres -v ON_ERROR_STOP=1 -c "select 1" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

docker compose exec -T -e PGPASSWORD=postgres support-db \
  psql -U supabase_admin -d postgres -v ON_ERROR_STOP=1 < db/init/001_schema.sql

docker compose exec -T -e PGPASSWORD=postgres support-db \
  psql -U supabase_admin -d postgres -v ON_ERROR_STOP=1 < db/init/002_seed.sql

docker compose up -d
python3 scripts/support_db.py health
